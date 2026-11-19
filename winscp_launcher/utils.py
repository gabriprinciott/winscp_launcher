"""Shared command, path, and subprocess helpers."""

import base64
import shlex
import subprocess
from pathlib import Path

from .logging_config import log


def command_text(cmd, secrets=()):
    if isinstance(cmd, list):
        parts = []
        redact_next = False
        previous_part = None

        for part in cmd:
            if redact_next:
                parts.append("***REDACTED***")
                redact_next = False
                previous_part = str(part)
                continue

            part = str(part)
            parts.append(shlex.quote(part))
            redact_next = previous_part == "sshpass" and part == "-p"
            previous_part = part

        rendered = " ".join(parts)
    else:
        rendered = str(cmd)

    for secret in secrets:
        if not secret:
            continue
        secret_text = str(secret)
        rendered = rendered.replace(secret_text, "***REDACTED***")
        encoded_secret = base64.b64encode(secret_text.encode("utf-8")).decode("ascii")
        rendered = rendered.replace(encoded_secret, "***REDACTED_BASE64***")

    return rendered


def sanitize_log_name(value):
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value))
    return safe.strip("._") or "session"


def run(cmd, check=True, secrets=(), display_cmd=None):
    pretty = display_cmd if display_cmd is not None else command_text(cmd, secrets)
    log.debug("EXEC: %s", pretty)
    result = subprocess.run(cmd, shell=isinstance(cmd, str), text=True)
    log.debug("RC=%s", result.returncode)

    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {pretty}")
    return result


def run_capture(cmd):
    log.debug("EXEC: %s", command_text(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def wsl_path(path):
    windows_path = str(Path(path).resolve())
    if len(windows_path) >= 2 and windows_path[1] == ":":
        drive = windows_path[0].lower()
        remainder = windows_path[2:].replace("\\", "/")
        return f"/mnt/{drive}{remainder}"
    if windows_path.startswith("/"):
        return windows_path
    raise ValueError(f"Cannot convert path to WSL format: {windows_path}")
