"""Command-line entry point supporting PuTTY flags and named arguments."""

from __future__ import annotations

import sys
from typing import Any

from .backends import get_backend
from .banner import print_banner
from .config import DEFAULT_PROMPT_REGEX
from .controller import controller_main
from .doctor import run_doctor
from .launcher import launch_ssh, validate_ssh_options
from .logging_config import log
from .sessions import (
    build_startup_commands,
    execute_pre_hooks,
    resolve_session_config,
)
from .ssh import ssh_log_path


def print_help() -> None:
    """Print complete CLI usage documentation and WinSCP macro guides."""
    print_banner(show_subtitle=True)
    print(r"""
USAGE:
  1. WinSCP PuTTY Drop-In Mode (Automatic):
     In WinSCP -> Preferences -> Integration -> Applications -> PuTTY path:
     Set to: C:\path\to\winscp_launcher\launcher.cmd
     WinSCP will invoke the launcher using standard PuTTY flags:
       launcher.cmd -ssh -P <port> -i <key.ppk> [-pw <password>] user@host

  2. WinSCP Custom Commands Mode (with Macros):
     In WinSCP -> Commands -> Open in Terminal / Custom commands:
       launcher.cmd --user "!u" --host "!@" --port "!#" --key "!k" --session "!N" --remote-dir "!/"

  3. Named Arguments Syntax:
     runner.py --user <user> --host <host> [options]

OPTIONS:
  -u, --user <username>       SSH remote username
  -H, --host <hostname>       SSH remote hostname or IP address
  -p, --port <port>           SSH remote port (default: 22)
  -k, --key <path>            Path to private key (.ppk, .pem, OpenSSH)
  -w, --password <pwd>        SSH password (redacted in logs)
  -s, --session <name>        WinSCP session name or profile key
  -d, --remote-dir <path>     Remote directory (WinSCP macro !/)
  --terminal <type>           Override terminal emulator (windows_terminal, wezterm, alacritty, conemu, cmd, custom)
  --backend <type>            Override SSH backend (wsl, native)
  --doctor                    Run environment diagnostics and verify dependencies
  -h, --help                  Show this help message and exit

PUTTY COMPATIBILITY FLAGS:
  -ssh                        Indicates SSH protocol (ignored)
  -P <port>                   SSH port
  -i <key>                    Private key file (.ppk or OpenSSH)
  -pw <password>              SSH password
  -load <session>             Load session settings by name
  -l <user>                   Remote user

WINSCP MACROS REFERENCE:
  !u   Username
  !@   Hostname / IP
  !#   Port number
  !k   Private key file path
  !p   Password (session password, or prompted)
  !P   Stored session password
  !N   Session name
  !/   Current remote directory (auto-navigated with cd)
  !s   Session URL (e.g. sftp://user@host:22/path)
""")


def parse_arguments(argv: list[str]) -> dict[str, Any]:
    """Parse PuTTY CLI flags and named options into a normalized connection request."""
    parsed: dict[str, Any] = {
        "user": None,
        "host": None,
        "port": 22,
        "key": None,
        "password": None,
        "session": None,
        "remote_dir": None,
        "terminal": None,
        "backend": None,
    }

    i = 0
    n = len(argv)
    while i < n:
        arg = argv[i]

        # PuTTY flags
        if arg == "-ssh":
            i += 1
            continue
        if arg == "-P" and i + 1 < n:
            parsed["port"] = argv[i + 1]
            i += 2
            continue
        if arg in ("-i", "--key", "-k") and i + 1 < n:
            parsed["key"] = argv[i + 1]
            i += 2
            continue
        if arg in ("-pw", "--password", "-w") and i + 1 < n:
            parsed["password"] = argv[i + 1]
            i += 2
            continue
        if arg in ("-load", "--session", "-s", "--session-name") and i + 1 < n:
            parsed["session"] = argv[i + 1]
            i += 2
            continue
        if arg in ("-l", "--user", "-u") and i + 1 < n:
            parsed["user"] = argv[i + 1]
            i += 2
            continue
        if arg in ("--host", "-H") and i + 1 < n:
            parsed["host"] = argv[i + 1]
            i += 2
            continue
        if arg in ("-p", "--port") and i + 1 < n:
            parsed["port"] = argv[i + 1]
            i += 2
            continue
        if arg in ("--remote-dir", "-d", "--dir") and i + 1 < n:
            parsed["remote_dir"] = argv[i + 1]
            i += 2
            continue
        if arg == "--terminal" and i + 1 < n:
            parsed["terminal"] = argv[i + 1]
            i += 2
            continue
        if arg == "--backend" and i + 1 < n:
            parsed["backend"] = argv[i + 1]
            i += 2
            continue

        # Target argument: user@host or host
        if not arg.startswith("-"):
            if "@" in arg:
                user_part, host_part = arg.split("@", 1)
                parsed["user"] = parsed["user"] or user_part
                parsed["host"] = parsed["host"] or host_part
            else:
                parsed["host"] = parsed["host"] or arg
            i += 1
            continue

        log.warning("Unknown or unsupported CLI argument: %s", arg)
        i += 1

    return parsed


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    args = sys.argv[1:] if argv is None else argv

    # 1. Controller mode for ConPTY child process
    if len(args) >= 2 and args[0] == "--controller":
        return int(controller_main(args[1]))

    # 2. Help and Diagnostics
    if not args or "-h" in args or "--help" in args:
        print_help()
        return 0

    if "--doctor" in args:
        return run_doctor()

    # 3. Parse options
    parsed = parse_arguments(args)
    user = parsed.get("user")
    host = parsed.get("host")
    port = parsed.get("port") or 22
    key = parsed.get("key")
    password = parsed.get("password")
    session = parsed.get("session") or host or "SSH Session"
    remote_dir = parsed.get("remote_dir")

    if not host:
        print(
            "Error: Target hostname is required.\nRun 'runner.py --help' for usage.",
            file=sys.stderr,
        )
        return 2

    title = f"{session} [{user}@{host}]" if user else f"{session} [{host}]"
    log.info("=" * 80)
    log.info("SESSION: %s (target: %s@%s:%s)", session, user, host, port)

    # 4. Resolve session configuration, rules, and profiles
    cli_overrides = {
        "terminal": parsed.get("terminal"),
        "backend": parsed.get("backend"),
    }
    effective_config = resolve_session_config(
        session_name=session,
        host=host,
        remote_dir=remote_dir,
        cli_overrides=cli_overrides,
    )

    # 5. Run pre-connection hooks
    execute_pre_hooks(effective_config.get("pre_hooks", []))

    # 6. Compose startup commands and prompt detection
    startup_commands = build_startup_commands(effective_config)
    prompt_regex = str(effective_config.get("start_prompt_regex") or DEFAULT_PROMPT_REGEX)
    ssh_extra_opts = validate_ssh_options(effective_config, prompt_regex)

    log.debug("STARTUP_COMMANDS count=%s", len(startup_commands or []))
    log.debug("START_PROMPT_REGEX=%s", prompt_regex)
    log.debug("SSH_LOG=%s", ssh_log_path(session))

    # 7. Resolve credential and authentication mode using the backend
    backend = get_backend(effective_config.get("backend"), effective_config)
    raw_credential = key if key else password
    auth_mode, credential = backend.prepare_credential(
        host=host,
        user=user or "",
        credential=raw_credential,
    )

    # 8. Check Operating System
    import os

    if os.name != "nt":
        print(
            f"Error: WinSCP Launcher requires Microsoft Windows to launch terminal sessions.\n"
            f"Detected OS: {sys.platform}. WinSCP and Windows ConPTY operate on Windows.\n"
            f"On Linux/macOS, you can run '--help', '--doctor', or execute the test suite.",
            file=sys.stderr,
        )
        return 1

    # 9. Launch ConPTY terminal session
    launch_ssh(
        user=user or "",
        host=host,
        port=port,
        title=title,
        auth_mode=auth_mode,
        credential=credential,
        ssh_extra_opts=ssh_extra_opts,
        startup_commands=startup_commands,
        prompt_regex=prompt_regex,
        effective_config=effective_config,
    )
    return 0
