"""Terminal emulator abstractions and command generators."""

from __future__ import annotations

import abc
import os
import shutil
import sys
from typing import Any

from .config import BASE_DIR, SCRIPT_PATH


class TerminalLauncher(abc.ABC):
    """Abstract base class for terminal launchers."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @abc.abstractmethod
    def build_command(self, title: str, encoded_payload: str) -> list[str]:
        """Build the command-line argument list to launch the terminal emulator."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check whether the required terminal emulator binary is available."""

    def _get_controller_command(self, encoded_payload: str) -> list[str]:
        """Return the python command that runs the ConPTY controller."""
        return [sys.executable, str(SCRIPT_PATH), "--controller", encoded_payload]


class WindowsTerminalLauncher(TerminalLauncher):
    """Windows Terminal (wt.exe) launcher."""

    def is_available(self) -> bool:
        return shutil.which("wt.exe") is not None or shutil.which("wt") is not None

    def build_command(self, title: str, encoded_payload: str) -> list[str]:
        profile = self.config.get("wt_profile") or os.environ.get("WT_PROFILE")
        window_mode = self.config.get("window_mode", "tab")  # "tab", "window", or "none"

        cmd = ["wt.exe"]
        if window_mode == "tab":
            cmd.extend(["-w", "0", "new-tab"])
        elif window_mode == "window":
            cmd.extend(["-w", "new"])

        if profile:
            cmd.extend(["--profile", str(profile)])

        cmd.extend(
            [
                "--title",
                title,
                "--startingDirectory",
                str(BASE_DIR),
                *self._get_controller_command(encoded_payload),
            ]
        )
        return cmd


class WezTermLauncher(TerminalLauncher):
    """WezTerm terminal launcher."""

    def is_available(self) -> bool:
        return shutil.which("wezterm") is not None or shutil.which("wezterm.exe") is not None

    def build_command(self, title: str, encoded_payload: str) -> list[str]:
        exe = shutil.which("wezterm") or shutil.which("wezterm.exe") or "wezterm"
        return [
            exe,
            "start",
            "--cwd",
            str(BASE_DIR),
            *self._get_controller_command(encoded_payload),
        ]


class AlacrittyLauncher(TerminalLauncher):
    """Alacritty terminal launcher."""

    def is_available(self) -> bool:
        return shutil.which("alacritty") is not None or shutil.which("alacritty.exe") is not None

    def build_command(self, title: str, encoded_payload: str) -> list[str]:
        exe = shutil.which("alacritty") or shutil.which("alacritty.exe") or "alacritty"
        return [
            exe,
            "--title",
            title,
            "--working-directory",
            str(BASE_DIR),
            "-e",
            *self._get_controller_command(encoded_payload),
        ]


class ConEmuLauncher(TerminalLauncher):
    """ConEmu terminal launcher."""

    def is_available(self) -> bool:
        return (
            shutil.which("ConEmu64.exe") is not None
            or shutil.which("ConEmu.exe") is not None
            or shutil.which("conemu") is not None
        )

    def build_command(self, title: str, encoded_payload: str) -> list[str]:
        exe = (
            shutil.which("ConEmu64.exe")
            or shutil.which("ConEmu.exe")
            or shutil.which("conemu")
            or "ConEmu64.exe"
        )
        return [
            exe,
            "-title",
            title,
            "-dir",
            str(BASE_DIR),
            "-run",
            *self._get_controller_command(encoded_payload),
        ]


class CmdLauncher(TerminalLauncher):
    """Native Windows Command Prompt launcher."""

    def is_available(self) -> bool:
        return True

    def build_command(self, title: str, encoded_payload: str) -> list[str]:
        return [
            "cmd.exe",
            "/c",
            "start",
            title,
            *self._get_controller_command(encoded_payload),
        ]


class CustomTerminalLauncher(TerminalLauncher):
    """User-defined custom terminal command template."""

    def is_available(self) -> bool:
        template = self.config.get("terminal_command")
        if not template:
            return False
        if isinstance(template, list) and template:
            return shutil.which(template[0]) is not None
        return True

    def build_command(self, title: str, encoded_payload: str) -> list[str]:
        template = self.config.get("terminal_command")
        if not template:
            raise ValueError(
                "custom terminal selected but 'terminal_command' is not defined in config"
            )

        controller_cmd = self._get_controller_command(encoded_payload)

        if isinstance(template, list):
            cmd: list[str] = []
            for item in template:
                if item == "{controller_cmd}":
                    cmd.extend(controller_cmd)
                else:
                    cmd.append(
                        item.replace("{title}", title)
                        .replace("{base_dir}", str(BASE_DIR))
                        .replace("{payload}", encoded_payload)
                        .replace("{python}", sys.executable)
                        .replace("{script}", str(SCRIPT_PATH))
                    )
            return cmd

        if isinstance(template, str):
            formatted = (
                template.replace("{title}", title)
                .replace("{base_dir}", str(BASE_DIR))
                .replace("{payload}", encoded_payload)
                .replace("{python}", sys.executable)
                .replace("{script}", str(SCRIPT_PATH))
                .replace("{controller_cmd}", " ".join(controller_cmd))
            )
            return formatted.split()

        raise TypeError(f"Invalid terminal_command format: {type(template)}")


TERMINAL_REGISTRY: dict[str, type[TerminalLauncher]] = {
    "windows_terminal": WindowsTerminalLauncher,
    "wt": WindowsTerminalLauncher,
    "wezterm": WezTermLauncher,
    "alacritty": AlacrittyLauncher,
    "conemu": ConEmuLauncher,
    "cmd": CmdLauncher,
    "custom": CustomTerminalLauncher,
}


def get_terminal_launcher(
    terminal_type: str | None = None,
    config: dict[str, Any] | None = None,
) -> TerminalLauncher:
    """Resolve and instantiate a TerminalLauncher instance."""
    resolved_type = (terminal_type or "windows_terminal").lower().strip()
    launcher_cls = TERMINAL_REGISTRY.get(resolved_type)
    if not launcher_cls:
        supported = ", ".join(TERMINAL_REGISTRY.keys())
        raise ValueError(
            f"Unsupported terminal type: '{terminal_type}'. Supported terminals: {supported}"
        )
    return launcher_cls(config)
