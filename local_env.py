from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = ROOT / ".env"
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_project_env(path: Path = DEFAULT_ENV_FILE, *, override: bool = False) -> dict[str, str]:
    if not path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or (not override and os.environ.get(key)):
            continue
        cleaned = _strip_quotes(value.strip())
        os.environ[key] = cleaned
        loaded[key] = cleaned
    return loaded


def read_env_file(path: Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        key = _line_key(raw_line)
        if key is None:
            continue
        values[key] = _strip_quotes(raw_line.split("=", 1)[1].strip())
    return values


def update_env_file(updates: Mapping[str, object], path: Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    cleaned_updates = {_validate_env_key(key): _validate_env_value(value) for key, value in updates.items()}
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(cleaned_updates)
    output_lines: list[str] = []

    for raw_line in existing_lines:
        key = _line_key(raw_line)
        if key is None or key not in remaining:
            output_lines.append(raw_line)
            continue
        output_lines.append(_format_env_line(key, remaining.pop(key)))

    if remaining:
        if output_lines and output_lines[-1].strip():
            output_lines.append("")
        for key in sorted(remaining):
            output_lines.append(_format_env_line(key, remaining[key]))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(output_lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return read_env_file(path)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _line_key(raw_line: str) -> str | None:
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key = line.split("=", 1)[0].strip()
    return key if ENV_KEY_PATTERN.match(key) else None


def _validate_env_key(key: object) -> str:
    rendered = str(key).strip()
    if not ENV_KEY_PATTERN.match(rendered):
        raise ValueError(f"invalid environment key: {key}")
    return rendered


def _validate_env_value(value: object) -> str:
    rendered = "" if value is None else str(value)
    if "\n" in rendered or "\r" in rendered:
        raise ValueError("environment values must be single-line strings")
    return rendered.strip()


def _format_env_line(key: str, value: str) -> str:
    return f"{key}={value}"
