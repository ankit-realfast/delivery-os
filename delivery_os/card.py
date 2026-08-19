from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

STATES = ["draft", "contest", "commit", "build", "verify", "observe", "closed"]


def state_index(state: str) -> int:
    return STATES.index(state)


def state_at_least(state: str, floor: str) -> bool:
    """Is `state` at or past `floor` in the loop?

    An unrecognised state is treated as past the floor: fail closed, so a
    typo can never buy a card an exemption from a check it should face.
    """
    try:
        return STATES.index(state) >= STATES.index(floor)
    except ValueError:
        return True


@dataclass
class Card:
    id: str
    title: str
    tier: str
    state: str
    path: Path | None = None
    parent: str | None = None
    decider: str | None = None
    eval: str | None = None
    behaviour_delta: str = "none"
    delta_owner: str | None = None
    value_line: str | None = None
    kill_criterion: str | None = None
    observation_date: date | None = None
    blocked_on: str | None = None
    touches_production_data: bool = False
    touches_auth: bool = False
    external_commitment: bool = False
    flag_off: bool = True
    value_moved: bool | None = None
    history: list[dict] = field(default_factory=list)
    intent: str = ""


_FIELD_NAMES = {f.name for f in dataclasses.fields(Card)}
# Loader-owned: derived from the file itself, never authored in frontmatter.
_LOADER_OWNED = {"path", "intent"}
_AUTHORABLE = _FIELD_NAMES - _LOADER_OWNED
# Line-anchored: a bare `---` line only. Free-text fields legitimately
# contain "---" (horizontal rules, em-dashes, pasted text).
_FRONTMATTER_RE = re.compile(r"(?m)^---\s*$")


def load_card(path: str | Path) -> Card:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    parts = _FRONTMATTER_RE.split(text, maxsplit=2)
    if len(parts) < 3 or parts[0].strip():
        raise ValueError(f"{path}: missing or unterminated YAML frontmatter")
    _, front, body = parts
    data = yaml.safe_load(front) or {}
    unknown = sorted(set(data) - _AUTHORABLE)
    if unknown:
        raise ValueError(f"{path}: unknown fields {unknown}")
    data["path"] = path
    data["intent"] = body.strip()
    return Card(**data)


def load_all(root: str | Path) -> list[Card]:
    cards = [load_card(p) for p in sorted(Path(root).rglob("*.md"))]
    return sorted(cards, key=lambda c: c.id)
