from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_FILENAME = ".delivery-os.yml"
CONFIG_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectConfig:
    project_root: Path
    schema_version: int = CONFIG_SCHEMA_VERSION
    cards_root: str = "cards"
    archive_root: str = "archive/cards"
    deciders_file: str = "contract/deciders.yml"
    default_eval_timeout_seconds: int = 300
    support_url: str = "https://github.com/ankit-realfast/delivery-os/issues"
    allowed_eval_environment: tuple[str, ...] = field(default_factory=tuple)

    def resolve(self, relative: str) -> Path:
        return (self.project_root / relative).resolve()

    @property
    def cards_path(self) -> Path:
        return self.resolve(self.cards_root)

    @property
    def archive_path(self) -> Path:
        return self.resolve(self.archive_root)

    @property
    def deciders_path(self) -> Path:
        return self.resolve(self.deciders_file)


def find_project_root(start: str | Path = ".") -> Path:
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / CONFIG_FILENAME).is_file() or (candidate / ".git").exists():
            return candidate
    return current


def load_config(start: str | Path = ".") -> ProjectConfig:
    root = find_project_root(start)
    path = root / CONFIG_FILENAME
    if not path.exists():
        return ProjectConfig(project_root=root)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: configuration must be a mapping")
    allowed = {
        "schema_version",
        "cards_root",
        "archive_root",
        "deciders_file",
        "default_eval_timeout_seconds",
        "support_url",
        "allowed_eval_environment",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"{path}: unknown configuration fields {unknown}")
    version = raw.get("schema_version", CONFIG_SCHEMA_VERSION)
    if version != CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"{path}: unsupported configuration schema_version {version}; "
            f"expected {CONFIG_SCHEMA_VERSION}"
        )
    timeout = raw.get("default_eval_timeout_seconds", 300)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError(f"{path}: default_eval_timeout_seconds must be positive")
    allowed_env = raw.get("allowed_eval_environment", [])
    if not isinstance(allowed_env, list) or not all(isinstance(v, str) for v in allowed_env):
        raise ValueError(f"{path}: allowed_eval_environment must be a list of names")
    text_fields = {
        name: raw.get(name, getattr(ProjectConfig(root), name))
        for name in ("cards_root", "archive_root", "deciders_file", "support_url")
    }
    for name, value in text_fields.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{path}: {name} must be non-empty text")
    config = ProjectConfig(
        project_root=root,
        schema_version=version,
        default_eval_timeout_seconds=timeout,
        allowed_eval_environment=tuple(allowed_env),
        **text_fields,
    )
    for name, candidate in (
        ("cards_root", config.cards_path),
        ("archive_root", config.archive_path),
        ("deciders_file", config.deciders_path),
    ):
        try:
            candidate.relative_to(root)
        except ValueError:
            raise ValueError(f"{path}: {name} must stay inside the project root") from None
    try:
        config.archive_path.relative_to(config.cards_path)
    except ValueError:
        pass
    else:
        raise ValueError(f"{path}: archive_root must be outside cards_root")
    return config


def default_config_text() -> str:
    data = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "cards_root": "cards",
        "archive_root": "archive/cards",
        "deciders_file": "contract/deciders.yml",
        "default_eval_timeout_seconds": 300,
        "support_url": "https://github.com/ankit-realfast/delivery-os/issues",
        "allowed_eval_environment": [],
    }
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def write_default_config(project_root: str | Path, *, force: bool = False) -> Path:
    root = Path(project_root).resolve()
    path = root / CONFIG_FILENAME
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists")
    root.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=root,
            prefix=f".{CONFIG_FILENAME}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(default_config_text())
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    return path
