"""Small local .env loader for repository orchestration scripts."""

from __future__ import annotations

import os
from pathlib import Path


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_project_env(project_root: Path | str, filename: str = ".env") -> dict[str, str]:
    """Load KEY=VALUE pairs from a project .env file without overriding os.environ."""
    env_path = Path(project_root) / filename
    loaded: dict[str, str] = {}

    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        value = _strip_quotes(value.strip())
        os.environ[key] = value
        loaded[key] = value

    return loaded

