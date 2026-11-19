"""Session configuration resolution, wildcard rule engine, and startup command builder."""

from __future__ import annotations

import fnmatch
import shlex
from typing import Any

from .config import (
    DEFAULT_BACKEND,
    DEFAULT_PROMPT_REGEX,
    DEFAULT_TERMINAL,
    load_app_config,
)
from .logging_config import log
from .utils import run


def parse_shorthand_profile(shorthand: str) -> dict[str, Any]:
    """Parse shorthand string syntax into a configuration dictionary.

    Examples:
        "prod-oracle" -> {"profile": "prod-oracle"}
        "ssh bastion | su - oracle" -> {"jump_command": "ssh bastion", "change_user": "oracle"}
        "ssh bastion | su - oracle | cd /var/log" -> {"jump_command": "ssh bastion", "change_user": "oracle", "start_directory": "/var/log"}
    """
    text = shorthand.strip()
    if "|" not in text:
        return {"profile": text}

    result: dict[str, Any] = {}
    parts = [part.strip() for part in text.split("|") if part.strip()]
    for part in parts:
        if part.startswith("ssh ") or part.startswith("jump "):
            result["jump_command"] = part
        elif part.startswith("su - "):
            result["change_user"] = part[5:].strip()
        elif part.startswith("su "):
            result["change_user"] = part[3:].strip()
        elif part.startswith("cd "):
            result["start_directory"] = part[3:].strip()
        else:
            result.setdefault("start_commands", []).append(part)
    return result


def resolve_profile(
    profile_name: str,
    all_profiles: dict[str, Any],
    seen: list[str] | None = None,
) -> dict[str, Any]:
    """Recursively resolve a profile and its parent inheritance hierarchy.

    Supports 'parent', 'extends', and 'inherits' properties (string or list of strings).
    Merges parent settings into child settings:
    - Scalar values (change_user, jump_command, etc.) are overridden by children.
    - List values (ssh_extra_opts, start_commands, pre_hooks) are appended (parent first, child second).
    Detects circular inheritance cycles and raises ValueError.
    """
    if profile_name not in all_profiles:
        log.warning("Referenced profile '%s' not found in profiles dictionary", profile_name)
        return {}

    chain = list(seen) if seen else []
    if profile_name in chain:
        cycle_path = " -> ".join(chain + [profile_name])
        raise ValueError(f"Circular profile inheritance detected: {cycle_path}")

    current_seen = chain + [profile_name]

    raw_data = all_profiles[profile_name]
    if isinstance(raw_data, str):
        profile_data = parse_shorthand_profile(raw_data)
    elif isinstance(raw_data, dict):
        profile_data = dict(raw_data)
    else:
        log.warning(
            "Profile '%s' must be a dict or string, got %s",
            profile_name,
            type(raw_data).__name__,
        )
        return {}

    # Extract parent reference(s) if any
    parent_val = (
        profile_data.get("parent") or profile_data.get("extends") or profile_data.get("inherits")
    )
    parents: list[str] = []
    if isinstance(parent_val, str):
        parents = [p.strip() for p in parent_val.split(",") if p.strip()]
    elif isinstance(parent_val, list):
        parents = [str(p).strip() for p in parent_val if p and str(p).strip()]

    resolved: dict[str, Any] = {}

    # 1. Resolve and merge parents in order
    for parent in parents:
        parent_config = resolve_profile(parent, all_profiles, current_seen)
        for k, v in parent_config.items():
            if k in ("parent", "extends", "inherits"):
                continue
            if k in ("ssh_extra_opts", "start_commands", "pre_hooks") and isinstance(v, list):
                resolved.setdefault(k, []).extend(v)
            else:
                resolved[k] = v

    # 2. Merge child's own properties (override scalars, extend lists)
    for k, v in profile_data.items():
        if k in ("parent", "extends", "inherits"):
            continue
        if k in ("ssh_extra_opts", "start_commands", "pre_hooks") and isinstance(v, list):
            resolved.setdefault(k, []).extend(v)
        else:
            resolved[k] = v

    return resolved


def apply_profile(
    target_config: dict[str, Any],
    profile_name: str,
    all_profiles: dict[str, Any],
) -> None:
    """Apply a named profile definition into target_config, resolving inheritance."""
    resolved_profile = resolve_profile(profile_name, all_profiles)
    if not resolved_profile:
        return

    for k, v in resolved_profile.items():
        if k == "ssh_extra_opts" and isinstance(v, list):
            target_config.setdefault("ssh_extra_opts", []).extend(v)
        elif k == "start_commands" and isinstance(v, list):
            target_config.setdefault("start_commands", []).extend(v)
        elif k == "pre_hooks" and isinstance(v, list):
            target_config.setdefault("pre_hooks", []).extend(v)
        else:
            target_config[k] = v


def match_wildcard(pattern: str | None, value: str | None) -> bool:
    """Check if value matches the glob pattern (case-insensitive)."""
    if not pattern or not value:
        return False
    return fnmatch.fnmatch(value.lower(), pattern.lower())


def resolve_session_config(
    session_name: str | None = None,
    host: str | None = None,
    remote_dir: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the effective configuration by combining defaults, wildcard rules, profiles, and overrides."""
    app_config = load_app_config()
    profiles: dict[str, Any] = app_config.get("profiles", {})
    rules: list[dict[str, Any]] = app_config.get("rules", [])
    sessions: dict[str, Any] = app_config.get("sessions", {})

    effective: dict[str, Any] = {
        "terminal": app_config.get("terminal", DEFAULT_TERMINAL),
        "backend": app_config.get("backend", DEFAULT_BACKEND),
        "wt_profile": app_config.get("wt_profile"),
        "wsl_distro": app_config.get("wsl_distro"),
        "ssh_extra_opts": list(app_config.get("ssh_extra_opts", [])),
        "start_directory": None,
        "start_commands": list(app_config.get("start_commands", [])),
        "start_prompt_regex": app_config.get("start_prompt_regex", DEFAULT_PROMPT_REGEX),
        "jump_command": None,
        "change_user": None,
        "pre_hooks": list(app_config.get("pre_hooks", [])),
    }

    # 1. Match wildcard rules
    for rule in rules:
        host_pattern = rule.get("host")
        session_pattern = rule.get("session")

        matched = False
        if (
            host_pattern
            and match_wildcard(host_pattern, host)
            or session_pattern
            and match_wildcard(session_pattern, session_name)
        ):
            matched = True

        if matched:
            log.debug("Rule matched: %s", rule)
            rule_profile = rule.get("profile") or rule.get("parent") or rule.get("extends")
            if rule_profile:
                apply_profile(effective, rule_profile, profiles)
            for k, v in rule.items():
                if k not in ("host", "session", "profile", "parent", "extends", "inherits"):
                    effective[k] = v

    # 2. Check explicit session override in sessions dictionary
    session_entry = None
    if session_name and session_name in sessions:
        session_entry = sessions[session_name]
    elif host and host in sessions:
        session_entry = sessions[host]

    if session_entry:
        if isinstance(session_entry, str):
            session_entry = parse_shorthand_profile(session_entry)

        if isinstance(session_entry, dict):
            session_profile = (
                session_entry.get("profile")
                or session_entry.get("parent")
                or session_entry.get("extends")
            )
            if session_profile:
                apply_profile(effective, session_profile, profiles)
            for k, v in session_entry.items():
                if k not in ("profile", "parent", "extends", "inherits"):
                    effective[k] = v

    # 3. Automatic remote directory fallback: if no explicit start_directory, use remote_dir from WinSCP (!/)
    if not effective.get("start_directory") and remote_dir and remote_dir.strip():
        log.info("Applying remote directory as start_directory: %s", remote_dir)
        effective["start_directory"] = remote_dir.strip()

    # 4. Apply CLI overrides
    if cli_overrides:
        for k, v in cli_overrides.items():
            if v is not None:
                effective[k] = v

    return effective


def execute_pre_hooks(hooks: list[str]) -> None:
    """Execute pre-connection hooks (batch files, powershell scripts, or commands)."""
    for hook in hooks:
        if not hook:
            continue
        log.info("Executing pre-connection hook: %s", hook)
        run(hook, check=True)


def build_startup_commands(config: dict[str, Any]) -> list[str] | None:
    """Compose the sequence of startup commands to send into ConPTY after prompt detection."""
    start_dir = config.get("start_directory")
    jump_cmd = config.get("jump_command")
    change_user = config.get("change_user")
    start_commands = config.get("start_commands") or []

    if start_dir is not None and not isinstance(start_dir, str):
        raise ValueError("start_directory must be a string or null")
    if jump_cmd is not None and not isinstance(jump_cmd, str):
        raise ValueError("jump_command must be a string or null")
    if change_user is not None:
        if not isinstance(change_user, str) or not change_user:
            raise ValueError("change_user must be a non-empty string or null")
        if "\x00" in change_user:
            raise ValueError("Invalid change_user")
    if not isinstance(start_commands, list):
        raise ValueError("start_commands must be a list")

    commands: list[str] = []
    if jump_cmd:
        commands.append(jump_cmd)
    if change_user:
        commands.append(f"su - {shlex.quote(change_user)}")
    if start_dir:
        commands.append(f"cd -- {shlex.quote(start_dir)}")
    commands.extend(start_commands)

    return commands or None
