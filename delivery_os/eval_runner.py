from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from delivery_os.card import Card

MAX_CAPTURE_CHARS = 1_000_000


@dataclass(frozen=True)
class EvalPlan:
    command: tuple[str, ...]
    preflight: tuple[str, ...] | None
    working_directory: Path
    environment: dict[str, str]
    timeout_seconds: int
    failure_exit_codes: tuple[int, ...]


@dataclass(frozen=True)
class EvalResult:
    outcome: str
    stdout: str
    stderr: str
    command: tuple[str, ...]
    exit_code: int | None
    duration_seconds: float
    timed_out: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "timed_out": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def _inside(base: Path, target: Path) -> bool:
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def plan_eval(
    card: Card,
    repo_root: str | Path = ".",
    *,
    default_timeout_seconds: int = 300,
    allowed_environment: tuple[str, ...] = (),
) -> EvalPlan:
    if not card.eval:
        raise ValueError("card has no eval command")
    root = Path(repo_root).resolve()
    if isinstance(card.eval, str):
        spec: dict[str, Any] = {
            "preflight": ["{python}", "-c", "import pytest"],
            "command": ["{python}", "-m", "pytest", card.eval, "-q"],
            "failure_exit_codes": [1],
        }
    else:
        spec = card.eval

    command = tuple(
        part.replace("{python}", sys.executable).replace("{repo}", str(root))
        for part in spec["command"]
    )
    preflight_spec = spec.get("preflight")
    preflight = (
        tuple(
            part.replace("{python}", sys.executable).replace("{repo}", str(root))
            for part in preflight_spec
        )
        if preflight_spec
        else None
    )
    workdir = (root / spec.get("working_directory", ".")).resolve()
    if not _inside(root, workdir):
        raise ValueError("eval working_directory must stay inside the repository")
    if not workdir.is_dir():
        raise ValueError(f"eval working_directory does not exist: {workdir}")

    explicit_env = dict(spec.get("environment", {}))
    forbidden = sorted(set(explicit_env) - set(allowed_environment))
    if forbidden:
        raise ValueError(
            "eval requests environment variables that are not allowed by "
            f".delivery-os.yml: {', '.join(forbidden)}"
        )
    return EvalPlan(
        command=command,
        preflight=preflight,
        working_directory=workdir,
        environment=explicit_env,
        timeout_seconds=int(spec.get("timeout_seconds", default_timeout_seconds)),
        failure_exit_codes=tuple(spec.get("failure_exit_codes", [1])),
    )


def command_available(plan: EvalPlan) -> bool:
    commands = [plan.command]
    if plan.preflight:
        commands.append(plan.preflight)
    for command in commands:
        executable = command[0]
        if os.sep in executable or (os.altsep and os.altsep in executable):
            if not Path(executable).is_file():
                return False
        elif shutil.which(executable) is None:
            return False
    return True


def _capture(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if len(value) <= MAX_CAPTURE_CHARS:
        return value
    return value[:MAX_CAPTURE_CHARS] + "\n[output truncated by delivery-os]\n"


def run_eval(plan: EvalPlan) -> EvalResult:
    if not command_available(plan):
        return EvalResult(
            outcome="error",
            stdout="",
            stderr=f"eval executable not found: {plan.command[0]}",
            command=plan.command,
            exit_code=None,
            duration_seconds=0.0,
        )
    env = os.environ.copy()
    env.update(plan.environment)
    if plan.preflight:
        try:
            checked = subprocess.run(
                list(plan.preflight),
                cwd=plan.working_directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=plan.timeout_seconds,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return EvalResult(
                outcome="error",
                stdout="",
                stderr=f"eval preflight failed: {exc}",
                command=plan.command,
                exit_code=None,
                duration_seconds=0.0,
            )
        if checked.returncode != 0:
            detail = _capture(checked.stderr) or _capture(checked.stdout)
            return EvalResult(
                outcome="error",
                stdout="",
                stderr=f"eval preflight exited {checked.returncode}: {detail}",
                command=plan.command,
                exit_code=checked.returncode,
                duration_seconds=0.0,
            )
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(plan.command),
            cwd=plan.working_directory,
            env=env,
            capture_output=True,
            text=True,
            timeout=plan.timeout_seconds,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return EvalResult(
            outcome="timeout",
            stdout=_capture(exc.stdout),
            stderr=_capture(exc.stderr),
            command=plan.command,
            exit_code=None,
            duration_seconds=round(time.monotonic() - started, 3),
            timed_out=True,
        )
    except OSError as exc:
        return EvalResult(
            outcome="error",
            stdout="",
            stderr=str(exc),
            command=plan.command,
            exit_code=None,
            duration_seconds=round(time.monotonic() - started, 3),
        )
    outcome = (
        "pass"
        if completed.returncode == 0
        else "fail"
        if completed.returncode in plan.failure_exit_codes
        else "error"
    )
    return EvalResult(
        outcome=outcome,
        stdout=_capture(completed.stdout),
        stderr=_capture(completed.stderr),
        command=plan.command,
        exit_code=completed.returncode,
        duration_seconds=round(time.monotonic() - started, 3),
    )
