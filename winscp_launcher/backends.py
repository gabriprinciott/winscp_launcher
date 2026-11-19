"""SSH Execution environment backends (WSL, Native Windows, Custom)."""

from __future__ import annotations

import abc
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .logging_config import log
from .utils import run, run_capture, wsl_path


def sanitize_key_name(host: str, user: str) -> str:
    """Sanitize host and username to form a safe filename for the converted key."""
    value = f"{host}_{user}"
    for character in "/\\ :()@":
        value = value.replace(character, "_")
    return value


class SSHBackend(abc.ABC):
    """Abstract base class for SSH execution backends."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @abc.abstractmethod
    def prepare_credential(
        self, host: str, user: str, credential: str | None
    ) -> tuple[str, str | None]:
        """Determine auth mode ('key', 'password', 'none') and prepare remote credential path if needed."""

    @abc.abstractmethod
    def build_inner_command(
        self,
        user: str,
        host: str,
        port: str | int,
        auth_mode: str,
        credential: str | None,
        ssh_extra_opts: list[str],
    ) -> list[str]:
        """Build the command executed inside ConPTY."""

    @abc.abstractmethod
    def check_health(self) -> list[str]:
        """Perform health checks and return a list of issue descriptions (empty if healthy)."""


class WSLBackend(SSHBackend):
    """Executes SSH inside a Windows Subsystem for Linux (WSL) distribution."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.distro = self.config.get("wsl_distro") or os.environ.get("WSL_DISTRO")

    def _wsl_cmd_prefix(self) -> list[str]:
        cmd = ["wsl.exe"]
        if self.distro:
            cmd.extend(["-d", self.distro])
        return cmd

    def prepare_credential(
        self, host: str, user: str, credential: str | None
    ) -> tuple[str, str | None]:
        if not credential:
            return "none", None

        # Check if credential is a path to a key file
        is_ppk = credential.lower().endswith(".ppk")
        is_key_path = (
            is_ppk
            or credential.lower().endswith((".pem", ".id_rsa", ".id_ed25519", ".key"))
            or Path(credential).is_file()
        )

        if not is_key_path:
            return "password", credential

        if not is_ppk:
            # It's an OpenSSH key; convert Windows path to WSL path
            return "key", wsl_path(credential)

        # Convert PPK to OpenSSH inside WSL using puttygen
        key_name = sanitize_key_name(host, user)
        wsl_prefix = ["wsl", "-d", self.distro] if self.distro else ["wsl"]

        try:
            wsl_home = run_capture([*wsl_prefix, "bash", "-lc", 'printf "%s" "$HOME"'])
        except Exception as exc:
            log.warning("Could not determine WSL $HOME, falling back to ~/.ssh: %s", exc)
            wsl_home = "~"

        remote_key = f"{wsl_home}/.ssh/winscp/{key_name}"
        wsl_ppk = wsl_path(credential)

        run([*wsl_prefix, "bash", "-lc", "mkdir -p ~/.ssh/winscp"])

        exists = subprocess.run(
            [*wsl_prefix, "bash", "-lc", f"test -f {shlex.quote(remote_key)}"],
            capture_output=True,
            check=False,
        )

        if exists.returncode != 0:
            log.info("Converting PPK key to OpenSSH format in WSL: %s", remote_key)
            conversion_command = shlex.join(
                ["puttygen", wsl_ppk, "-O", "private-openssh", "-o", remote_key]
            )
            chmod_command = shlex.join(["chmod", "600", remote_key])
            run([*wsl_prefix, "bash", "-lc", f"{conversion_command} && {chmod_command}"])
        else:
            log.debug("OpenSSH key already exists: %s", remote_key)

        return "key", remote_key

    def build_inner_command(
        self,
        user: str,
        host: str,
        port: str | int,
        auth_mode: str,
        credential: str | None,
        ssh_extra_opts: list[str],
    ) -> list[str]:
        target = f"{user}@{host}" if user else host
        ssh_args = [*ssh_extra_opts, "-p", str(port), "-tt", target]

        if auth_mode == "key" and credential:
            ssh_cmd = ["ssh", "-i", credential, *ssh_args]
        elif auth_mode == "password" and credential:
            ssh_cmd = [
                "sshpass",
                "-p",
                credential,
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                *ssh_args,
            ]
        else:
            ssh_cmd = ["ssh", *ssh_args]

        return [*self._wsl_cmd_prefix(), "--exec", *ssh_cmd]

    def check_health(self) -> list[str]:
        issues: list[str] = []
        if not shutil.which("wsl.exe") and not shutil.which("wsl"):
            return ["wsl.exe was not found in PATH."]

        wsl_prefix = ["wsl", "-d", self.distro] if self.distro else ["wsl"]
        # Check if WSL distro responds
        try:
            res = subprocess.run(
                [*wsl_prefix, "uname"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if res.returncode != 0:
                distro_msg = f" '{self.distro}'" if self.distro else " (default)"
                issues.append(f"WSL distro{distro_msg} failed to run: {res.stderr.strip()}")
                return issues
        except Exception as exc:
            issues.append(f"WSL check error: {exc}")
            return issues

        # Check packages in WSL: ssh, puttygen, sshpass
        for tool, pkg_tip in [
            ("ssh", "openssh-client"),
            ("puttygen", "putty-tools (Debian/Ubuntu) or putty (RHEL/OracleLinux)"),
            ("sshpass", "sshpass"),
        ]:
            check = subprocess.run(
                [*wsl_prefix, "which", tool],
                capture_output=True,
                text=True,
                check=False,
            )
            if check.returncode != 0:
                issues.append(f"Tool '{tool}' is not installed in WSL. Install: {pkg_tip}")

        return issues


class NativeWindowsBackend(SSHBackend):
    """Executes native Windows OpenSSH client directly without WSL."""

    def prepare_credential(
        self, host: str, user: str, credential: str | None
    ) -> tuple[str, str | None]:
        if not credential:
            return "none", None

        is_key_path = (
            credential.lower().endswith((".pem", ".id_rsa", ".id_ed25519", ".key", ".ppk"))
            or Path(credential).is_file()
        )
        if is_key_path:
            return "key", credential
        return "password", credential

    def build_inner_command(
        self,
        user: str,
        host: str,
        port: str | int,
        auth_mode: str,
        credential: str | None,
        ssh_extra_opts: list[str],
    ) -> list[str]:
        target = f"{user}@{host}" if user else host
        ssh_cmd = ["ssh.exe", *ssh_extra_opts, "-p", str(port), "-tt", target]

        if auth_mode == "key" and credential:
            ssh_cmd.extend(["-i", credential])

        return ssh_cmd

    def check_health(self) -> list[str]:
        issues: list[str] = []
        if not shutil.which("ssh.exe") and not shutil.which("ssh"):
            issues.append("ssh.exe (Windows OpenSSH client) was not found in PATH.")
        return issues


BACKEND_REGISTRY: dict[str, type[SSHBackend]] = {
    "wsl": WSLBackend,
    "native": NativeWindowsBackend,
    "windows": NativeWindowsBackend,
}


def get_backend(
    backend_type: str | None = None,
    config: dict[str, Any] | None = None,
) -> SSHBackend:
    """Resolve and instantiate an SSHBackend instance."""
    resolved = (backend_type or "wsl").lower().strip()
    backend_cls = BACKEND_REGISTRY.get(resolved)
    if not backend_cls:
        supported = ", ".join(BACKEND_REGISTRY.keys())
        raise ValueError(
            f"Unsupported backend type: '{backend_type}'. Supported backends: {supported}"
        )
    return backend_cls(config)
