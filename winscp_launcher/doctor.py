"""Diagnostic and environment health check utility (--doctor)."""

from __future__ import annotations

import sys
from typing import Any

from .banner import print_banner
from .config import find_config_file


def run_doctor() -> int:
    """Run full environment diagnostics and print a health report."""
    print_banner(show_subtitle=True)
    print("\n🔍 Running WinSCP Launcher Environment Diagnostics...\n")

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Operating System Check
    import os
    import platform

    os_name = platform.system()
    print(f"[*] Host Operating System: {os_name} ({sys.platform})", end="", flush=True)
    if os.name == "nt":
        print("  [OK]")
    else:
        print("  [NOTE] (Non-Windows host)")
        warnings.append(
            f"WinSCP Launcher is designed to run on Windows (where WinSCP and ConPTY operate). "
            f"You are currently running on {os_name}. Unit tests and CLI parsing work here, "
            f"but terminal launching with ConPTY requires Windows."
        )

    # 2. Python Version Check
    py_ver = sys.version_info
    print(f"[*] Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}", end="", flush=True)
    if py_ver >= (3, 9):
        print("  [OK]")
    else:
        print("  [ERROR] (Requires Python 3.9+)")
        errors.append("Python 3.9 or higher is required.")

    # 3. Dependency Check: json5
    print("[*] Required Package 'json5':", end="", flush=True)
    try:
        import json5  # noqa: F401

        print("  [OK]")
    except ImportError:
        print("  [ERROR] (Missing)")
        errors.append(
            "The 'json5' library is missing. Install with: pip install -r requirements.txt"
        )

    # 4. Configuration File Check
    cfg_file = find_config_file()
    print("[*] Configuration File:", end="", flush=True)
    cfg_data: dict[str, Any] = {}
    if cfg_file:
        print(f"  [OK] ({cfg_file.name})")
        try:
            from .jsonc import load_jsonc_file

            cfg_data = load_jsonc_file(cfg_file)
            print("    - Syntax check: Valid JSON/JSON5 object  [OK]")
            profiles = cfg_data.get("profiles", {})
            rules = cfg_data.get("rules", [])
            sessions = cfg_data.get("sessions", {})
            print(
                f"    - Loaded: {len(profiles)} profiles, {len(rules)} rules, {len(sessions)} session overrides"
            )

            # Validate profile inheritance and detect circular references
            from .sessions import resolve_profile

            for prof_name in profiles:
                try:
                    resolve_profile(prof_name, profiles)
                except ValueError as val_err:
                    print(f"    - Profile error in '{prof_name}': {val_err}  [ERROR]")
                    errors.append(f"Profile '{prof_name}' inheritance error: {val_err}")
        except Exception as exc:
            print(f"    - Syntax check: Failed ({exc})  [ERROR]")
            errors.append(f"Configuration file error: {exc}")
    else:
        print("  [WARN] (config.json5 not found)")
        warnings.append(
            "No config.json5 found. Copy config.example.json5 to config.json5 to customize."
        )

    # 5. Terminal Emulator Check
    terminal_type = cfg_data.get("terminal", "windows_terminal")
    print(f"[*] Terminal Emulator ('{terminal_type}'):", end="", flush=True)
    try:
        from .terminals import get_terminal_launcher

        launcher = get_terminal_launcher(terminal_type, cfg_data)
        if launcher.is_available():
            print("  [OK]")
        else:
            print("  [ERROR] (Executable not found in PATH)")
            errors.append(
                f"Terminal emulator '{terminal_type}' executable is not available in PATH."
            )
    except Exception as exc:
        print(f"  [ERROR] ({exc})")
        errors.append(f"Terminal error: {exc}")

    # 6. Backend Execution Environment Check
    backend_type = cfg_data.get("backend", "wsl")
    print(f"[*] SSH Backend ('{backend_type}'):", end="", flush=True)
    try:
        from .backends import get_backend

        backend = get_backend(backend_type, cfg_data)
        issues = backend.check_health()
        if not issues:
            print("  [OK]")
        else:
            print("  [ISSUES DETECTED]")
            for issue in issues:
                print(f"    - {issue}")
                if "wsl.exe was not found" in issue or "not installed in WSL" in issue:
                    errors.append(issue)
                else:
                    warnings.append(issue)
    except Exception as exc:
        print(f"  [ERROR] ({exc})")
        errors.append(f"Backend check error: {exc}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ Diagnostics FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"   • {err}")
        return 1

    if warnings:
        print(f"⚠️  Diagnostics completed with {len(warnings)} warning(s):")
        for warn in warnings:
            print(f"   • {warn}")
        print("\nThe launcher can still run, but some optional features may be limited.")
        return 0

    print("✅ All systems operational! WinSCP Launcher is ready to use.")
    return 0
