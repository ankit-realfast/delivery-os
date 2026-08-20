from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

STATES = ["draft", "contest", "commit", "build", "verify", "observe", "closed"]
CURRENT_SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = (0, CURRENT_SCHEMA_VERSION)


class ConcurrentWriteError(RuntimeError):
    """The card changed on disk after this process loaded it."""


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
    # Version 0 means a legacy card with no authored schema_version.
    schema_version: int = 0
    path: Path | None = None
    parent: str | None = None
    decider: str | None = None
    eval: str | dict[str, Any] | None = None
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
    # Did the declared behaviour delta hold? Spec 5's M3 guard:
    # "Declaring 'none' falsely -> the observation date checks the
    # claim against reality." None until observed.
    delta_held: bool | None = None
    history: list[dict] = field(default_factory=list)
    intent: str = ""
    # Which keys the author actually wrote. Loader-owned; lets dump_card
    # round-trip a deliberate `eval: null` placeholder without inflating
    # every other field to its default.
    authored_keys: frozenset[str] = frozenset()
    # Frontmatter key -> one-based source line, used for actionable lint output.
    field_lines: dict[str, int] = field(default_factory=dict)
    # Optimistic concurrency token. Loader-owned and never serialized.
    source_digest: str | None = None


_FIELD_NAMES = {f.name for f in dataclasses.fields(Card)}
# Loader-owned: derived from the file itself, never authored in frontmatter.
_LOADER_OWNED = {"path", "intent", "authored_keys", "field_lines", "source_digest"}
_AUTHORABLE = _FIELD_NAMES - _LOADER_OWNED
# Line-anchored: a bare `---` line only. Free-text fields legitimately
# contain "---" (horizontal rules, em-dashes, pasted text).
_FRONTMATTER_RE = re.compile(r"(?m)^---\s*$")


# --- type coercion ----------------------------------------------------------
# The loader validated field NAMES but never their types. Unquoted
#   at: 2026-08-01T09:00:00Z
# resolves to a datetime and crashed meters._last_entry_at; quoted
#   observation_date: "2026-09-30"
# stays a str and crashed compute_scoreboard's `<= today`. Both lint clean
# and take down `dos report` for the entire corpus.

_TEXT_FIELDS = {
    "id",
    "title",
    "tier",
    "state",
    "parent",
    "decider",
    "behaviour_delta",
    "delta_owner",
    "value_line",
    "kill_criterion",
    "blocked_on",
}
_BOOL_FIELDS = {
    "touches_production_data",
    "touches_auth",
    "external_commitment",
    "flag_off",
    "value_moved",
    "delta_held",
}
_REQUIRED = ("id", "title", "tier", "state")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _as_text(path: Path, key: str, raw: object) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (date, datetime)):
        return raw.isoformat()
    if isinstance(raw, (int, float, bool)):
        return str(raw)
    raise ValueError(f"{path}: '{key}' must be text, got {type(raw).__name__}")


def _as_bool(path: Path, key: str, raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    raise ValueError(f"{path}: '{key}' must be true or false, got {type(raw).__name__} {raw!r}")


def _as_date(path: Path, key: str, raw: object) -> date:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw)
        except ValueError:
            raise ValueError(f"{path}: '{key}' must be a YYYY-MM-DD date, got {raw!r}") from None
    raise ValueError(f"{path}: '{key}' must be a date, got {type(raw).__name__}")


def _as_schema_version(path: Path, raw: object) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise ValueError(f"{path}: 'schema_version' must be an integer, got {type(raw).__name__}")
    if raw not in SUPPORTED_SCHEMA_VERSIONS:
        supported = ", ".join(str(v) for v in SUPPORTED_SCHEMA_VERSIONS)
        raise ValueError(
            f"{path}: unsupported schema_version {raw}; this delivery-os release "
            f"supports {supported}. Upgrade delivery-os before changing this card."
        )
    return raw


def _as_eval(path: Path, raw: object) -> str | dict[str, Any]:
    """Accept legacy pytest strings and v1 language-neutral command specs."""
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: 'eval' must be a command mapping, got {type(raw).__name__}")
    allowed = {
        "command",
        "preflight",
        "timeout_seconds",
        "working_directory",
        "environment",
        "failure_exit_codes",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"{path}: eval has unknown fields {unknown}")

    command = raw.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(part, str) and part for part in command)
    ):
        raise ValueError(f"{path}: eval.command must be a non-empty list of strings")

    preflight = raw.get("preflight")
    if preflight is not None and (
        not isinstance(preflight, list)
        or not preflight
        or not all(isinstance(part, str) and part for part in preflight)
    ):
        raise ValueError(f"{path}: eval.preflight must be a non-empty list of strings")

    timeout = raw.get("timeout_seconds", 300)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError(f"{path}: eval.timeout_seconds must be a positive integer")

    working_directory = raw.get("working_directory", ".")
    if not isinstance(working_directory, str) or not working_directory:
        raise ValueError(f"{path}: eval.working_directory must be text")

    environment = raw.get("environment", {})
    if not isinstance(environment, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in environment.items()
    ):
        raise ValueError(f"{path}: eval.environment must map text names to text values")

    failure_codes = raw.get("failure_exit_codes", [1])
    if (
        not isinstance(failure_codes, list)
        or not failure_codes
        or not all(
            isinstance(code, int) and not isinstance(code, bool) and code != 0
            for code in failure_codes
        )
    ):
        raise ValueError(
            f"{path}: eval.failure_exit_codes must be a non-empty list of non-zero integers"
        )

    normalized: dict[str, Any] = {"command": list(command)}
    if preflight is not None:
        normalized["preflight"] = list(preflight)
    if "timeout_seconds" in raw:
        normalized["timeout_seconds"] = timeout
    if "working_directory" in raw:
        normalized["working_directory"] = working_directory
    if "environment" in raw:
        normalized["environment"] = dict(environment)
    if "failure_exit_codes" in raw:
        normalized["failure_exit_codes"] = list(failure_codes)
    return normalized


def _as_history(path: Path, raw: object) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError(f"{path}: 'history' must be a list, got {type(raw).__name__}")
    out: list[dict] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: history[{i}] must be a mapping, got {type(entry).__name__}")
        item = dict(entry)
        at = item.get("at")
        if at is None:
            raise ValueError(f"{path}: history[{i}] has no 'at' timestamp")
        if isinstance(at, datetime):
            at = at.isoformat()
        elif not isinstance(at, str):
            raise ValueError(
                f"{path}: history[{i}].at must be a timestamp, got {type(at).__name__}"
            )
        try:
            stamp = datetime.fromisoformat(at)
        except ValueError:
            raise ValueError(f"{path}: history[{i}].at is not an ISO timestamp: {at!r}") from None
        if stamp.tzinfo is None:
            # M1 subtracts these from an aware `now`; mixing naive and aware
            # raises TypeError and takes down `dos report` for every card.
            raise ValueError(f"{path}: history[{i}].at needs a timezone offset, got {at!r}")
        item["at"] = stamp.isoformat()
        for key in (
            "state",
            "by",
            "verify",
            "observed",
            "delta",
            "approved_by",
            "approval_evidence",
            "pull_request",
        ):
            if key in item and item[key] is not None:
                item[key] = _as_text(path, f"history[{i}].{key}", item[key])
        if "command" in item:
            command = item["command"]
            if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
                raise ValueError(f"{path}: history[{i}].command must be a list of strings")
        if "exit_code" in item and not isinstance(item["exit_code"], int):
            raise ValueError(f"{path}: history[{i}].exit_code must be an integer")
        if "duration_seconds" in item and not isinstance(item["duration_seconds"], (int, float)):
            raise ValueError(f"{path}: history[{i}].duration_seconds must be a number")
        out.append(item)
    return out


def _coerce(path: Path, data: dict) -> dict:
    out: dict = {}
    for key, raw in data.items():
        if raw is None:
            # `key: null` means "unset"; the dataclass default applies. This
            # keeps template placeholders (eval: null) legal.
            continue
        if key == "history":
            out[key] = _as_history(path, raw)
        elif key == "schema_version":
            out[key] = _as_schema_version(path, raw)
        elif key == "eval":
            out[key] = _as_eval(path, raw)
        elif key == "observation_date":
            out[key] = _as_date(path, key, raw)
        elif key in _BOOL_FIELDS:
            out[key] = _as_bool(path, key, raw)
        elif key in _TEXT_FIELDS:
            out[key] = _as_text(path, key, raw)
        else:  # pragma: no cover - defensive
            out[key] = raw
    missing = [k for k in _REQUIRED if not out.get(k)]
    if missing:
        raise ValueError(f"{path}: missing required field(s) {missing}")
    return out


def _split_frontmatter(text: str, path: Path) -> tuple[str, str] | None:
    """(frontmatter, body), or None when the file has no card frontmatter.

    A leading UTF-8 BOM is stripped before looking for the opening fence, so
    it cannot disguise a real card as one with no frontmatter.

    A file with no opening `---` fence at all is not a card -- a README,
    notes, a template -- and returns None so `load_all` can skip it quietly.
    A file that DOES open a fence but never closes it IS a card, just a
    broken one: raise, don't swallow it, or a typo'd closing fence makes the
    card invisible to `dos lint` instead of failing it.
    """
    if text.startswith("﻿"):
        text = text[1:]
    parts = _FRONTMATTER_RE.split(text, maxsplit=2)
    if parts[0].strip():
        return None
    if len(parts) == 1:
        return None
    if len(parts) == 2:
        raise ValueError(
            f"{path}: unterminated YAML frontmatter (opening '---' fence is never closed)"
        )
    return parts[1], parts[2]


def _build_card(path: Path, text: str) -> Card:
    split = _split_frontmatter(text, path)
    if split is None:
        raise ValueError(f"{path}: missing YAML frontmatter")
    front, body = split
    data = yaml.safe_load(front) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    unknown = sorted(set(data) - _AUTHORABLE)
    if unknown:
        raise ValueError(f"{path}: unknown fields {unknown}")
    fields = _coerce(path, data)
    fields["path"] = path
    fields["intent"] = body.strip()
    fields["authored_keys"] = frozenset(data)
    fields["field_lines"] = {
        match.group(1): line_number
        for line_number, line in enumerate(front.splitlines(), start=2)
        if (match := re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", line))
    }
    fields["source_digest"] = _digest(text)
    return Card(**fields)


def load_card(path: str | Path) -> Card:
    path = Path(path)
    return _build_card(path, path.read_text(encoding="utf-8"))


def load_all(root: str | Path) -> list[Card]:
    """Every card under `root`, sorted by id.

    A `.md` file with no opening `---` fence at all (a README, notes, a
    template) is skipped rather than raising: the corpus directory is a
    normal directory that people put files in, and `dos lint` crashing with
    a traceback on a README is worse than ignoring it. A file that DOES open
    a frontmatter fence but is malformed -- including an opening fence that
    is never closed -- still raises: that is a broken card, not a non-card,
    and must not go invisible to `dos lint` and the scoreboard.
    """
    cards: list[Card] = []
    for p in sorted(Path(root).rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        if _split_frontmatter(text, p) is None:
            continue
        cards.append(_build_card(p, text))
    return sorted(cards, key=lambda c: c.id)


_NO_DEFAULT = object()


def _default_for(f: dataclasses.Field) -> object:
    if f.default is not dataclasses.MISSING:
        return f.default
    if f.default_factory is not dataclasses.MISSING:
        return f.default_factory()
    return _NO_DEFAULT


def dump_card(card: Card) -> str:
    """Serialise a card back to the file format load_card reads.

    Single owner of the format: cli._rewrite used to rebuild the frontmatter
    layout itself and re-hardcode ("path", "intent"), duplicating
    _LOADER_OWNED. It also wrote EVERY dataclass field, so a three-field T1
    card became an eighteen-field card on its first transition. Spec 8 names
    exactly that -- "T1 cards carrying more than three fields" -- as the most
    likely way this OS dies.

    A field is written only when the author wrote it, or when its value has
    moved off the dataclass default. Fields the author never mentioned and
    never changed stay out of the file.
    """
    data: dict = {}
    if "schema_version" in card.authored_keys or card.schema_version != 0:
        data["schema_version"] = card.schema_version
    for f in dataclasses.fields(Card):
        if f.name in _LOADER_OWNED or f.name == "schema_version":
            continue
        value = getattr(card, f.name)
        if f.name in card.authored_keys or value != _default_for(f):
            data[f.name] = value
    front = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return f"---\n{front}---\n{card.intent}\n"


def write_card(card: Card, *, force: bool = False) -> None:
    """Atomically overwrite a card, refusing to lose a concurrent edit."""
    if card.path is None:
        raise ValueError(f"{card.id}: card has no path to write to")
    path = Path(card.path)
    if path.exists() and card.source_digest and not force:
        current = path.read_text(encoding="utf-8")
        if _digest(current) != card.source_digest:
            raise ConcurrentWriteError(
                f"{card.id}: {path} changed after it was loaded; reload and retry "
                "instead of overwriting another person's work"
            )

    rendered = dump_card(card)
    path.parent.mkdir(parents=True, exist_ok=True)
    old_mode = path.stat().st_mode if path.exists() else None
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        if old_mode is not None:
            os.chmod(temp_path, old_mode)
        os.replace(temp_path, path)
        card.source_digest = _digest(rendered)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def migrate_card(card: Card) -> Card:
    """Return the current-schema representation of a legacy card."""
    if card.schema_version == CURRENT_SCHEMA_VERSION and not isinstance(card.eval, str):
        return card
    if card.schema_version not in {0, CURRENT_SCHEMA_VERSION}:
        raise ValueError(f"{card.id}: cannot migrate schema {card.schema_version}")

    eval_spec = card.eval
    if isinstance(eval_spec, str):
        eval_spec = {
            "preflight": ["{python}", "-c", "import pytest"],
            "command": ["{python}", "-m", "pytest", eval_spec, "-q"],
            "timeout_seconds": 300,
            "working_directory": ".",
            "environment": {},
            "failure_exit_codes": [1],
        }
    return dataclasses.replace(
        card,
        schema_version=CURRENT_SCHEMA_VERSION,
        eval=eval_spec,
        authored_keys=card.authored_keys | {"schema_version", "eval"},
    )
