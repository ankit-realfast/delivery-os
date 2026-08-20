from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from delivery_os.card import Card, ConcurrentWriteError, load_all, write_card
from delivery_os.config import ProjectConfig
from delivery_os.lint import effective_tier, tier_reasons
from delivery_os.machine import LEGAL_TRANSITIONS

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_EVAL_ERROR = 3
EXIT_CONFLICT = 4


@dataclass(frozen=True)
class CommandContext:
    config: ProjectConfig
    root: Path
    cards: list[Card]
    as_json: bool


def json_default(value: object) -> object:
    if isinstance(value, (date, datetime, Path)):
        return value.isoformat() if not isinstance(value, Path) else str(value)
    if isinstance(value, frozenset):
        return sorted(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def emit(payload: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=json_default))
    elif isinstance(payload, str):
        print(payload)
    else:
        print(payload)


def error(message: str, *, as_json: bool, code: str = "error") -> None:
    if as_json:
        print(json.dumps({"error": code, "message": message}, indent=2), file=sys.stderr)
    else:
        print(message, file=sys.stderr)


def atomic_create(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"{path} already exists")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.link(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_replace(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def card_dict(card: Card) -> dict[str, Any]:
    result: dict[str, Any] = {}
    hidden = {"path", "intent", "authored_keys", "source_digest"}
    for field in dataclasses.fields(card):
        if field.name not in hidden:
            result[field.name] = getattr(card, field.name)
    result["path"] = str(card.path) if card.path else None
    result["intent"] = card.intent
    result["effective_tier"] = effective_tier(card)
    result["review_reasons"] = tier_reasons(card)
    return result


def find_card(cards: list[Card], card_id: str) -> Card | None:
    return next((card for card in cards if card.id == card_id), None)


def find_card_or_error(context: CommandContext, card_id: str) -> Card | None:
    matches = [card for card in context.cards if card.id == card_id]
    if not matches:
        error(
            f"No card with ID {card_id} exists under {context.root}.",
            as_json=context.as_json,
            code="card_not_found",
        )
        return None
    if len(matches) > 1:
        paths = ", ".join(str(card.path) for card in matches)
        error(
            f"Multiple cards claim {card_id}: {paths}",
            as_json=context.as_json,
            code="duplicate_card_id",
        )
        return None
    return matches[0]


def load_cards(root: Path, *, as_json: bool) -> tuple[list[Card] | None, int]:
    try:
        return load_all(root), EXIT_OK
    except (ValueError, OSError) as exc:
        error(f"Cannot load cards: {exc}", as_json=as_json, code="card_load_error")
        return None, EXIT_USAGE


def write_or_conflict(card: Card, *, as_json: bool) -> int:
    try:
        write_card(card)
        return EXIT_OK
    except ConcurrentWriteError as exc:
        error(str(exc), as_json=as_json, code="concurrent_write")
        return EXIT_CONFLICT


def next_states(card: Card) -> list[str]:
    legal = list(LEGAL_TRANSITIONS.get(card.state, []))
    if effective_tier(card) == "T1" and card.state == "draft":
        legal.append("commit")
    return sorted(set(legal))
