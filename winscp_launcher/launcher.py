"""Build and launch terminal sessions using ConPTY controller."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from .backends import get_backend
from .logging_config import log
from .terminals import get_terminal_launcher
from .utils import run


def launch_ssh(
    user: str,
    host: str,
    port: str | int,
    title: str,
    auth_mode: str,
    credential: str | None,
    ssh_extra_opts: list[str],
    startup_commands: list[str] | None,
    prompt_regex: str,
    effective_config: dict[str, Any],
) -> None:
    """Launch the terminal emulator running the ConPTY controller."""
    # 1. Resolve backend and build the inner SSH command
    backend = get_backend(effective_config.get("backend"), effective_config)
    inner_cmd = backend.build_inner_command(
        user=user,
        host=host,
        port=port,
        auth_mode=auth_mode,
        credential=credential,
        ssh_extra_opts=ssh_extra_opts,
    )

    # 2. Package payload for the ConPTY controller child process
    payload = {
        "command": inner_cmd,
        "startup_commands": startup_commands,
        "prompt_regex": prompt_regex,
    }
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")

    # 3. Resolve the terminal emulator and build the outer launcher command
    terminal_launcher = get_terminal_launcher(effective_config.get("terminal"), effective_config)
    terminal_cmd = terminal_launcher.build_command(title, encoded_payload)

    password_secret = (credential,) if auth_mode == "password" and credential else ()
    log.info("Launching terminal session: %s", title)
    run(
        terminal_cmd,
        check=False,
        secrets=password_secret,
        display_cmd=f"[{effective_config.get('terminal', 'terminal')}] {title} [ConPTY controller; payload redacted]",
    )


def validate_ssh_options(config: dict[str, Any], prompt_regex: str) -> list[str]:
    """Validate SSH options and prompt regular expression."""
    ssh_extra_opts = config.get("ssh_extra_opts", [])
    if not isinstance(ssh_extra_opts, list):
        raise ValueError("ssh_extra_opts must be a list")
    if not all(isinstance(option, str) for option in ssh_extra_opts):
        raise ValueError("Every ssh_extra_opts item must be a string")
    if not isinstance(prompt_regex, str) or not prompt_regex:
        raise ValueError("start_prompt_regex must be a non-empty string")
    re.compile(prompt_regex)
    return ssh_extra_opts
