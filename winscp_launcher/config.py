"""Application paths and environment configuration."""

import os
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = BASE_DIR / "runner.py"
LOG_DIR = BASE_DIR / "logs"
SSH_LOG_DIR = LOG_DIR / "ssh"

CONFIG_FILE_JSON5 = BASE_DIR / "config.json5"
CONFIG_FILE_JSON = BASE_DIR / "config.json"
CONFIG_EXAMPLE_JSON5 = BASE_DIR / "config.example.json5"

DEFAULT_TERMINAL = "windows_terminal"
DEFAULT_BACKEND = "wsl"
DEFAULT_PROMPT_REGEX = (
    r"^(?:\[[^\]\r\n]+\]|[^\r\n]*@[^\r\n]+(?::[^\r\n]*)?)"
    r"\s*[#$]\s*$"
)


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a file without overriding existing environment variables."""
    if not path.exists():
        return

    with path.open(encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key:
                os.environ.setdefault(key, value)


# Load optional .env file
load_env_file(BASE_DIR / ".env")

LOG_DIR.mkdir(exist_ok=True)
SSH_LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "winscp-launcher.log"
DEBUG_LOG_FILE = LOG_DIR / "winscp-launcher.debug.log"


def find_config_file() -> Path | None:
    """Find the active configuration file (config.json5 or config.json)."""
    if CONFIG_FILE_JSON5.exists():
        return CONFIG_FILE_JSON5
    if CONFIG_FILE_JSON.exists():
        return CONFIG_FILE_JSON
    return None


def load_app_config() -> dict[str, Any]:
    """Load the central application configuration if available."""
    config_file = find_config_file()
    if not config_file:
        return {}

    from .jsonc import load_jsonc_file

    return load_jsonc_file(config_file)
