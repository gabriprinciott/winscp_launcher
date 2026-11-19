"""SSH path helpers and key sanitization utilities."""

from pathlib import Path

from .config import SSH_LOG_DIR
from .utils import sanitize_log_name


def ssh_log_path(session_name: str | None) -> Path:
    """Return the log file path for a given session."""
    name = session_name or "default"
    return SSH_LOG_DIR / f"{sanitize_log_name(name)}.log"


def sanitize_key_name(host: str, user: str) -> str:
    """Sanitize host and username to form a safe filename for the converted key."""
    value = f"{host}_{user}"
    for character in "/\\ :()@":
        value = value.replace(character, "_")
    return value
