"""Unit tests for terminal launcher command generation."""

from winscp_launcher.terminals import (
    AlacrittyLauncher,
    CmdLauncher,
    CustomTerminalLauncher,
    WezTermLauncher,
    WindowsTerminalLauncher,
    get_terminal_launcher,
)


def test_windows_terminal_launcher_tab():
    config = {"wt_profile": "OracleLinux8", "window_mode": "tab"}
    launcher = WindowsTerminalLauncher(config)
    cmd = launcher.build_command("My Title", "payload123")
    assert cmd[0] == "wt.exe"
    assert "-w" in cmd
    assert "0" in cmd
    assert "new-tab" in cmd
    assert "--profile" in cmd
    assert "OracleLinux8" in cmd
    assert "--title" in cmd
    assert "My Title" in cmd
    assert "--controller" in cmd
    assert "payload123" in cmd


def test_windows_terminal_launcher_no_profile():
    launcher = WindowsTerminalLauncher({"window_mode": "window"})
    cmd = launcher.build_command("My Title", "payload123")
    assert cmd[0] == "wt.exe"
    assert "-w" in cmd
    assert "new" in cmd
    assert "--profile" not in cmd


def test_wezterm_launcher():
    launcher = WezTermLauncher()
    cmd = launcher.build_command("Title", "payload")
    assert "start" in cmd
    assert "--controller" in cmd
    assert "payload" in cmd


def test_alacritty_launcher():
    launcher = AlacrittyLauncher()
    cmd = launcher.build_command("Title", "payload")
    assert "--title" in cmd
    assert "Title" in cmd
    assert "-e" in cmd
    assert "--controller" in cmd


def test_cmd_launcher():
    launcher = CmdLauncher()
    cmd = launcher.build_command("Title", "payload")
    assert cmd[0] == "cmd.exe"
    assert "start" in cmd


def test_custom_terminal_launcher():
    config = {
        "terminal_command": [
            "myterm.exe",
            "--window-title",
            "{title}",
            "{controller_cmd}",
        ]
    }
    launcher = CustomTerminalLauncher(config)
    cmd = launcher.build_command("CustomTitle", "payloadABC")
    assert cmd[0] == "myterm.exe"
    assert cmd[1] == "--window-title"
    assert cmd[2] == "CustomTitle"
    assert "--controller" in cmd
    assert "payloadABC" in cmd


def test_get_terminal_launcher_factory():
    wt = get_terminal_launcher("windows_terminal")
    assert isinstance(wt, WindowsTerminalLauncher)

    wez = get_terminal_launcher("wezterm")
    assert isinstance(wez, WezTermLauncher)
