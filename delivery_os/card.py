from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from datetime import date, datetime
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


# --- type coercion ----------------------------------------------------------
# The loader validated field NAMES but never their types. Unquoted
#   at: 2026-08-01T09:00:00Z
# resolves to a datetime and crashed meters._last_entry_at; quoted
#   observation_date: "2026-09-30"
# stays a str and crashed compute_scoreboard's `<= today`. Both lint clean
# and take down `dos report` for the entire corpus.

_TEXT_FIELDS = {
    "id", "title", "tier", "state", "parent", "decider", "eval",
    "behaviour_delta", "delta_owner", "value_line", "kill_criterion",
    "blocked_on",
}
_BOOL_FIELDS = {
    "touches_production_data", "touches_auth", "external_commitment",
    "flag_off", "value_moved",
}
_REQUIRED = ("id", "title", "tier", "state")


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
    raise ValueError(
        f"{path}: '{key}' must be true or false, got {type(raw).__name__} {raw!r}"
    )


def _as_date(path: Path, key: str, raw: object) -> date:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw)
        except ValueError:
            raise ValueError(
                f"{path}: '{key}' must be a YYYY-MM-DD date, got {raw!r}"
            ) from None
    raise ValueError(f"{path}: '{key}' must be a date, got {type(raw).__name__}")


def _as_history(path: Path, raw: object) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError(f"{path}: 'history' must be a list, got {type(raw).__name__}")
    out: list[dict] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"{path}: history[{i}] must be a mapping, got {type(entry).__name__}"
            )
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
            raise ValueError(
                f"{path}: history[{i}].at is not an ISO timestamp: {at!r}"
            ) from None
        if stamp.tzinfo is None:
            # M1 subtracts these from an aware `now`; mixing naive and aware
            # raises TypeError and takes down `dos report` for every card.
            raise ValueError(
                f"{path}: history[{i}].at needs a timezone offset, got {at!r}"
            )
        item["at"] = stamp.isoformat()
        for key in ("state", "by", "verify"):
            if key in item and item[key] is not None:
                item[key] = _as_text(path, f"history[{i}].{key}", item[key])
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
        elif key == "observation_date":
            out[key] = _as_date(path, key, raw)
        elif key in _BOOL_FIELDS:
            out[key] = _as_bool(path, key, raw)
        elif key in _TEXT_FIELDS:
            out[key] = _as_text(path, key, raw)
        else:                                    # pragma: no cover - defensive
            out[key] = raw
    missing = [k for k in _REQUIRED if not out.get(k)]
    if missing:
        raise ValueError(f"{path}: missing required field(s) {missing}")
    return out


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    """(frontmatter, body), or None when the file has no card frontmatter."""
    parts = _FRONTMATTER_RE.split(text, maxsplit=2)
    if len(parts) < 3 or parts[0].strip():
        return None
    return parts[1], parts[2]


def _build_card(path: Path, text: str) -> Card:
    split = _split_frontmatter(text)
    if split is None:
        raise ValueError(f"{path}: missing or unterminated YAML frontmatter")
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
    return Card(**fields)


def load_card(path: str | Path) -> Card:
    path = Path(path)
    return _build_card(path, path.read_text(encoding="utf-8"))


def load_all(root: str | Path) -> list[Card]:
    """Every card under `root`, sorted by id.

    A `.md` file with no card frontmatter (a README, notes, a template) is
    skipped rather than raising: the corpus directory is a normal directory
    that people put files in, and `dos lint` crashing with a traceback on a
    README is worse than ignoring it. A file that DOES have frontmatter but
    is malformed still raises -- that is a broken card, not a non-card.
    """
    cards: list[Card] = []
    for p in sorted(Path(root).rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        if _split_frontmatter(text) is None:
            continue
        cards.append(_build_card(p, text))
    return sorted(cards, key=lambda c: c.id)
