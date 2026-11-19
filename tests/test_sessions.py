import pytest

from winscp_launcher.sessions import (
    apply_profile,
    build_startup_commands,
    match_wildcard,
    parse_shorthand_profile,
    resolve_profile,
    resolve_session_config,
)


def test_parse_shorthand():
    res1 = parse_shorthand_profile("prod-oracle")
    assert res1 == {"profile": "prod-oracle"}

    res2 = parse_shorthand_profile("ssh bastion.corp | su - oracle | cd /opt/oracle")
    assert res2["jump_command"] == "ssh bastion.corp"
    assert res2["change_user"] == "oracle"
    assert res2["start_directory"] == "/opt/oracle"


def test_match_wildcard():
    assert match_wildcard("*.prod.internal", "db1.prod.internal")
    assert match_wildcard("*.prod.internal", "DB1.PROD.INTERNAL")
    assert not match_wildcard("*.prod.internal", "db1.dev.internal")

    assert match_wildcard("10.20.*", "10.20.1.5")
    assert not match_wildcard("10.20.*", "192.168.1.1")

    assert match_wildcard("AWS-*", "AWS-Production")
    assert not match_wildcard("AWS-*", "Azure-Production")


def test_build_startup_commands():
    config = {
        "jump_command": "ssh bastion.company.com",
        "change_user": "oracle",
        "start_directory": "/var/log/oracle",
        "start_commands": ["ls -la", "echo ready"],
    }
    cmds = build_startup_commands(config)
    assert cmds == [
        "ssh bastion.company.com",
        "su - oracle",
        "cd -- /var/log/oracle",
        "ls -la",
        "echo ready",
    ]


def test_remote_dir_fallback():
    # If config doesn't specify a start_directory, remote_dir is applied
    effective = resolve_session_config(
        session_name="TestSession",
        host="test.example.com",
        remote_dir="/home/app/deep/logs",
    )
    assert effective["start_directory"] == "/home/app/deep/logs"

    # Startup commands will include cd to that directory
    cmds = build_startup_commands(effective)
    assert "cd -- /home/app/deep/logs" in cmds


def test_profile_inheritance_basic():
    profiles = {
        "corp-bastion": {
            "jump_command": "ssh bastion.company.com",
            "terminal": "windows_terminal",
            "change_user": "defaultuser",
        },
        "prod-oracle": {
            "parent": "corp-bastion",
            "change_user": "oracle",
            "start_directory": "/u01/app/oracle",
        },
    }
    resolved = resolve_profile("prod-oracle", profiles)
    assert resolved["jump_command"] == "ssh bastion.company.com"
    assert resolved["terminal"] == "windows_terminal"
    assert resolved["change_user"] == "oracle"
    assert resolved["start_directory"] == "/u01/app/oracle"
    assert "parent" not in resolved


def test_profile_inheritance_extends_alias():
    profiles = {
        "base": {
            "jump_command": "ssh jump.corp",
            "backend": "wsl",
        },
        "child": {
            "extends": "base",
            "wsl_distro": "Debian",
        },
    }
    resolved = resolve_profile("child", profiles)
    assert resolved["jump_command"] == "ssh jump.corp"
    assert resolved["backend"] == "wsl"
    assert resolved["wsl_distro"] == "Debian"
    assert "extends" not in resolved


def test_profile_inheritance_lists_concatenation():
    profiles = {
        "base": {
            "ssh_extra_opts": ["-o", "ServerAliveInterval=30"],
            "start_commands": ["echo base_ready"],
            "pre_hooks": ["pre_check.sh"],
        },
        "child": {
            "parent": "base",
            "ssh_extra_opts": ["-o", "StrictHostKeyChecking=no"],
            "start_commands": ["source ~/.bashrc", "uptime"],
            "pre_hooks": ["vpn_check.sh"],
        },
    }
    resolved = resolve_profile("child", profiles)
    assert resolved["ssh_extra_opts"] == [
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "StrictHostKeyChecking=no",
    ]
    assert resolved["start_commands"] == ["echo base_ready", "source ~/.bashrc", "uptime"]
    assert resolved["pre_hooks"] == ["pre_check.sh", "vpn_check.sh"]


def test_profile_inheritance_multi_level():
    profiles = {
        "grandparent": {
            "jump_command": "ssh root-bastion",
            "ssh_extra_opts": ["-o", "ForwardAgent=yes"],
            "change_user": "guest",
        },
        "parent": {
            "parent": "grandparent",
            "change_user": "middle_user",
            "start_commands": ["echo middle"],
        },
        "child": {
            "parent": "parent",
            "change_user": "final_app_user",
            "start_commands": ["echo child"],
            "start_directory": "/app/data",
        },
    }
    resolved = resolve_profile("child", profiles)
    assert resolved["jump_command"] == "ssh root-bastion"
    assert resolved["ssh_extra_opts"] == ["-o", "ForwardAgent=yes"]
    assert resolved["change_user"] == "final_app_user"
    assert resolved["start_commands"] == ["echo middle", "echo child"]
    assert resolved["start_directory"] == "/app/data"


def test_profile_inheritance_multiple_parents():
    profiles = {
        "base-network": {
            "jump_command": "ssh bastion.network",
            "ssh_extra_opts": ["-o", "ServerAliveInterval=60"],
        },
        "base-db": {
            "change_user": "dbadmin",
            "start_commands": ["export DB_HOME=/opt/db"],
        },
        "app-server": {
            "parent": ["base-network", "base-db"],
            "start_directory": "/opt/db/data",
        },
    }
    resolved = resolve_profile("app-server", profiles)
    assert resolved["jump_command"] == "ssh bastion.network"
    assert resolved["ssh_extra_opts"] == ["-o", "ServerAliveInterval=60"]
    assert resolved["change_user"] == "dbadmin"
    assert resolved["start_commands"] == ["export DB_HOME=/opt/db"]
    assert resolved["start_directory"] == "/opt/db/data"


def test_profile_inheritance_circular_detection():
    profiles = {
        "profileA": {"parent": "profileB"},
        "profileB": {"parent": "profileC"},
        "profileC": {"parent": "profileA"},
    }
    with pytest.raises(ValueError, match="Circular profile inheritance detected"):
        resolve_profile("profileA", profiles)

    # Self-referencing cycle
    profiles_self = {"self": {"parent": "self"}}
    with pytest.raises(ValueError, match="Circular profile inheritance detected: self -> self"):
        resolve_profile("self", profiles_self)


def test_profile_inheritance_missing_parent(caplog):
    profiles = {
        "child": {
            "parent": "non_existent_profile",
            "change_user": "appuser",
        }
    }
    # Should not raise exception, logs a warning and resolves child fields
    resolved = resolve_profile("child", profiles)
    assert resolved["change_user"] == "appuser"


def test_profile_inheritance_shorthand_parent():
    profiles = {
        "jump-shorthand": "ssh bastion.corp | su - oracle",
        "child": {
            "parent": "jump-shorthand",
            "start_directory": "/opt/oracle",
        },
    }
    resolved = resolve_profile("child", profiles)
    assert resolved["jump_command"] == "ssh bastion.corp"
    assert resolved["change_user"] == "oracle"
    assert resolved["start_directory"] == "/opt/oracle"


def test_apply_profile_integration():
    profiles = {
        "base": {
            "jump_command": "ssh base.jump",
            "ssh_extra_opts": ["-o", "ServerAliveInterval=45"],
        },
        "child": {
            "parent": "base",
            "change_user": "oracle",
            "ssh_extra_opts": ["-o", "StrictHostKeyChecking=no"],
        },
    }
    target = {"ssh_extra_opts": ["-o", "Compression=yes"]}
    apply_profile(target, "child", profiles)

    assert target["jump_command"] == "ssh base.jump"
    assert target["change_user"] == "oracle"
    assert target["ssh_extra_opts"] == [
        "-o",
        "Compression=yes",
        "-o",
        "ServerAliveInterval=45",
        "-o",
        "StrictHostKeyChecking=no",
    ]


def test_resolve_session_config_with_mocked_app_config(monkeypatch):
    mock_config = {
        "terminal": "windows_terminal",
        "backend": "wsl",
        "profiles": {
            "corp-bastion": {
                "jump_command": "ssh bastion.company.com",
                "ssh_extra_opts": ["-o", "ServerAliveInterval=60"],
            },
            "prod-oracle": {
                "parent": "corp-bastion",
                "change_user": "oracle",
            },
        },
        "rules": [
            {
                "host": "*.prod.internal",
                "parent": "prod-oracle",
                "start_directory": "/u01/app",
            }
        ],
        "sessions": {
            "Special-DB": {
                "extends": "prod-oracle",
                "change_user": "custom_oracle",
            }
        },
    }
    monkeypatch.setattr("winscp_launcher.sessions.load_app_config", lambda: mock_config)

    # 1. Test rule matching with parent profile inheritance
    rule_res = resolve_session_config(host="db01.prod.internal")
    assert rule_res["jump_command"] == "ssh bastion.company.com"
    assert rule_res["change_user"] == "oracle"
    assert rule_res["start_directory"] == "/u01/app"
    assert rule_res["ssh_extra_opts"] == ["-o", "ServerAliveInterval=60"]

    # 2. Test explicit session entry with extends and user override
    session_res = resolve_session_config(session_name="Special-DB", host="db02.prod.internal")
    assert session_res["jump_command"] == "ssh bastion.company.com"
    assert session_res["change_user"] == "custom_oracle"
