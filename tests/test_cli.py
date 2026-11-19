"""Unit tests for CLI argument parsing and PuTTY compatibility."""

from winscp_launcher.cli import parse_arguments


def test_parse_putty_standard_flags():
    argv = [
        "-ssh",
        "-P",
        "2222",
        "-i",
        "C:\\Users\\user\\.ssh\\key.ppk",
        "-pw",
        "secret_pass",
        "-load",
        "Production_DB",
        "oracle@10.0.0.15",
    ]
    parsed = parse_arguments(argv)
    assert parsed["user"] == "oracle"
    assert parsed["host"] == "10.0.0.15"
    assert parsed["port"] == "2222"
    assert parsed["key"] == "C:\\Users\\user\\.ssh\\key.ppk"
    assert parsed["password"] == "secret_pass"
    assert parsed["session"] == "Production_DB"


def test_parse_named_arguments():
    argv = [
        "--user",
        "deploy",
        "--host",
        "app.corp.internal",
        "--port",
        "2200",
        "--key",
        "/keys/deploy.pem",
        "--session",
        "AppServer",
        "--remote-dir",
        "/var/www/html",
        "--terminal",
        "wezterm",
        "--backend",
        "native",
    ]
    parsed = parse_arguments(argv)
    assert parsed["user"] == "deploy"
    assert parsed["host"] == "app.corp.internal"
    assert parsed["port"] == "2200"
    assert parsed["key"] == "/keys/deploy.pem"
    assert parsed["session"] == "AppServer"
    assert parsed["remote_dir"] == "/var/www/html"
    assert parsed["terminal"] == "wezterm"
    assert parsed["backend"] == "native"


def test_parse_target_without_user():
    argv = ["192.168.1.100", "-P", "22"]
    parsed = parse_arguments(argv)
    assert parsed["user"] is None
    assert parsed["host"] == "192.168.1.100"
    assert parsed["port"] == "22"


def test_parse_mixed_flags():
    argv = [
        "-u",
        "admin",
        "-H",
        "router.local",
        "-d",
        "/etc/config",
    ]
    parsed = parse_arguments(argv)
    assert parsed["user"] == "admin"
    assert parsed["host"] == "router.local"
    assert parsed["remote_dir"] == "/etc/config"
