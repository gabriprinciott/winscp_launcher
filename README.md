# WinSCP Launcher

<p align="center">
  <b>Smart Terminal &amp; Jump Host Automation Bridge for WinSCP</b><br>
  <i>Replace PuTTY in WinSCP with modern Windows terminals (Windows Terminal, WezTerm, Alacritty), automatically navigate jump hosts (bastions), switch application users (<code>su -</code>), and land directly in WinSCP's active remote folder.</i>
</p>

<p align="center">
  <a href="#-features"><img src="https://img.shields.io/badge/OS-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white" alt="Windows Support"></a>
  <a href="#-prerequisites-and-installation"><img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+"></a>
  <a href="#-conpty-native-controller"><img src="https://img.shields.io/badge/ConPTY-Native%20Win32%20API-success?logo=gnometerminal&logoColor=white" alt="ConPTY Native"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://mypy-lang.org/"><img src="https://img.shields.io/badge/types-Mypy%20Strict-blue" alt="Mypy"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

---

## 📑 Table of Contents

- [Why WinSCP Launcher?](#-why-winscp-launcher)
- [Key Features](#-key-features)
- [Architecture &amp; How It Works](#-architecture--how-it-works)
- [Prerequisites &amp; Installation](#-prerequisites--installation)
- [WinSCP Setup Guide](#-winscp-setup-guide)
  - [Method 1: Drop-in PuTTY Replacement (Recommended)](#method-1-drop-in-putty-replacement-recommended-)
  - [Method 2: Custom Commands (Right-Click Context Menu)](#method-2-custom-commands-right-click-context-menu)
- [WinSCP Macros Cheat Sheet](#-winscp-macros-cheat-sheet)
- [Configuration Guide (`config.json5`)](#-configuration-guide-configjson5)
  - [1. Global Settings](#1-global-settings)
  - [2. Profile Inheritance &amp; Overrides](#2-profile-inheritance--overrides)
  - [3. Wildcard Rules Engine](#3-wildcard-rules-engine)
  - [4. Session Overrides &amp; Pipeline Shorthand](#4-session-overrides--pipeline-shorthand)
- [Supported Terminal Emulators](#-supported-terminal-emulators)
- [SSH Execution Backends (WSL vs Native)](#-ssh-execution-backends-wsl-vs-native)
- [CLI Reference &amp; PuTTY Compatibility](#-cli-reference--putty-compatibility)
- [Security, Privacy &amp; Credential Redaction](#-security-privacy--credential-redaction)
- [Diagnostics &amp; Health Check (`--doctor`)](#-diagnostics--health-check---doctor)
- [Troubleshooting &amp; FAQ](#-troubleshooting--faq)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Why WinSCP Launcher?

WinSCP is arguably the finest graphical SFTP/SCP client on Windows, yet its terminal launch integration has historically remained tied to **PuTTY**:

- ❌ **PuTTY lacks modern features**: No tab support, dated font rendering, rigid styling, and inconvenient split panes.
- ❌ **Repetitive jump host friction**: If reaching a target host requires traversing a **bastion / jump server** followed by a `su - <service_user>`, you are forced to re-type SSH commands, passwords, and directories manually every single time.
- ❌ **Enterprise boundary constraints**: In enterprise Windows environments, installing native OpenSSH or managing complex SSH tunnel configurations is frequently blocked, whereas **WSL (Windows Subsystem for Linux)** is readily available and capable.
- ❌ **Lost remote context**: When browsing deep directory structures in WinSCP (e.g. `/var/log/nginx/` or `/u01/app/oracle/oradata`), opening PuTTY dumps you into the default home directory (`~`), requiring manual `cd` navigation.

### ✨ How WinSCP Launcher Changes Everything

1. **Seamless Drop-In PuTTY Replacement**: Place `launcher.cmd` into WinSCP’s preferences where `putty.exe` used to live. Pressing <kbd>Ctrl</kbd>+<kbd>P</kbd> or clicking the PuTTY toolbar icon invokes your modern terminal transparently.
2. **Zero-Dependency Native ConPTY Automation**: An embedded, pure-Python Windows Pseudo Console (ConPTY) orchestrator monitors shell output streams, detects the prompt using regex, and autonomously injects jump commands, `su -`, and `cd` commands. No external C++ compilations, pywin32 bindings, or heavy GUI automation tools needed.
3. **Instant Remote Directory Sync (`!/`)**: Passing WinSCP's remote folder macro (`!/`) instructs the launcher to automatically execute `cd` into the exact folder you are browsing in WinSCP.
4. **Hierarchical Profile Inheritance**: Organize complex server fleets cleanly. Child profiles inherit bastion connections, keepalive flags, and default users from parent profiles, overriding only specific settings (e.g. `change_user`, `start_directory`).
5. **Wildcard Rule Engine**: Map server groups automatically by domain (`*.prod.internal`) or IP subnet (`10.20.*`) without configuring individual sessions one by one.
6. **Broad Terminal Freedom**: Out-of-the-box support for Windows Terminal (tabs or standalone windows), WezTerm, Alacritty, ConEmu, native Command Prompt, or custom terminal binaries.

---

## 🚀 Architecture & How It Works

```
┌────────────────────────────────────────────────────────┐
│                        WinSCP                          │
│     (Toolbar Icon, Ctrl+P, or Custom Commands Menu)    │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ Invokes with PuTTY flags or macros
                            ▼
┌────────────────────────────────────────────────────────┐
│               launcher.cmd / runner.py                 │
│  - Parses PuTTY arguments & custom CLI parameters      │
│  - Evaluates wildcard rules & inherits profile configs │
│  - Triggers pre-connection hooks (VPN, token checkers) │
│  - Prepares credentials (converts .ppk if WSL backend) │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ Launches configured terminal emulator
                            ▼
┌────────────────────────────────────────────────────────┐
│          External Terminal (e.g. Windows Terminal)     │
│        Opens new tab/window titled: [user@host]        │
│          Executes internal ConPTY controller           │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Python ConPTY Child Controller             │
│  - Spawns Windows Pseudo Console (CreatePseudoConsole) │
│  - Launches backend SSH client (inside WSL or Native)  │
│  - Scans byte stream for remote shell prompt regex     │
│  - Injects startup pipeline:                           │
│      1. jump_command   (e.g. ssh bastion.internal)     │
│      2. change_user    (e.g. su - oracle)              │
│      3. start_directory(e.g. cd -- /var/log/nginx)     │
│      4. start_commands (e.g. source ~/.env)            │
│  - Seamlessly yields full interactive PTY to user      │
└────────────────────────────────────────────────────────┘
```

---

## 📦 Prerequisites & Installation

> [!IMPORTANT]
> **Operating System Requirement: Microsoft Windows 10 (Build 1809+) or Windows 11**
> WinSCP Launcher is designed to run directly on Windows (the host OS where WinSCP and Windows Pseudo Console live). If you select the **WSL backend**, Linux acts as the SSH execution sandbox inside Windows, but the launcher itself runs on Windows.

### 1. Requirements on Windows
- **Windows 10 / 11** (with ConPTY support, present in Windows 10 version 1809 and later).
- **Python 3.9+** installed on Windows and registered in your `PATH`.
- Your preferred terminal emulator:
  - **Windows Terminal** (pre-installed on Windows 11, or install via Microsoft Store / `winget install Microsoft.WindowsTerminal`)
  - **WezTerm**, **Alacritty**, or **ConEmu**.

### 2. Requirements in WSL (When using the `"wsl"` backend)
Inside your target WSL Linux distribution (e.g., Ubuntu, Debian, Oracle Linux), ensure standard SSH tools are present:
- **Debian / Ubuntu**:
  ```bash
  sudo apt update && sudo apt install -y openssh-client putty-tools sshpass
  ```
- **RHEL / Rocky / AlmaLinux / Oracle Linux / Fedora**:
  ```bash
  sudo dnf install -y openssh-clients putty sshpass
  ```

### 3. Installation
1. Clone the repository into your preferred tools folder (e.g. `C:\Tools\winscp_launcher`):
   ```cmd
   git clone https://github.com/gabriprinciott/winscp_launcher.git C:\Tools\winscp_launcher
   cd C:\Tools\winscp_launcher
   ```
2. Install the required Python dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
3. Copy the configuration template to create your live configuration:
   ```cmd
   copy config.example.json5 config.json5
   ```

### 4. Health Check Diagnostics (`--doctor`)
Run the diagnostic suite to verify your environment, dependencies, terminal, and configuration:
```cmd
python runner.py --doctor
:: or via the batch wrapper:
launcher.cmd --doctor
```

---

## ⚙️ WinSCP Setup Guide

You can integrate WinSCP Launcher in two ways. **Method 1** is recommended for complete transparency.

### Method 1: Drop-in PuTTY Replacement (Recommended ⭐)

This completely replaces standard PuTTY with your modern terminal. Whenever you press <kbd>Ctrl</kbd>+<kbd>P</kbd> or click the terminal icon on the WinSCP toolbar, WinSCP Launcher will open your session.

1. In WinSCP, open **Options ➔ Preferences** (<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>P</kbd>).
2. Navigate to **Integration ➔ Applications**.
3. Under **PuTTY path**, enter:
   ```cmd
   cmd.exe /c ""C:\Tools\winscp_launcher\launcher.cmd" --user "!u" --host "!@" --port "!#" --key "!k" --password "!P" --session "!N" --remote-dir "!/""
   ```
   *(Ensure you replace `C:\Tools\winscp_launcher` with your actual installation directory).*
4. *(Optional)* Check **"Remember session password and pass it to PuTTY"** if you want automated password authentication via `sshpass`.
5. Click **OK**. You are set!

```
┌────────────────────────────────────────────────────────────────────────┐
│ Preferences -> Integration -> Applications                            │
├────────────────────────────────────────────────────────────────────────┤
│ PuTTY/Terminal path:                                                   │
│ [ cmd.exe /c ""C:\Tools\winscp_launcher\launcher.cmd" ... "!/" ]  [...] │
│                                                                        │
│ [X] Remember session password and pass it to PuTTY                     │
└────────────────────────────────────────────────────────────────────────┘
```

### Method 2: Custom Commands (Right-Click Context Menu)

If you prefer keeping PuTTY intact and adding WinSCP Launcher as a custom command available in right-click menus:

1. Open **Options ➔ Preferences ➔ Commands** (or **Custom Commands**).
2. Click **Add**:
   - **Name**: `Open in Windows Terminal`
   - **Custom Command**:
     ```cmd
     cmd.exe /c ""C:\Tools\winscp_launcher\launcher.cmd" --user "!u" --host "!@" --port "!#" --key "!k" --password "!P" --session "!N" --remote-dir "!/""
     ```
   - Check **"Execute in new window"** (Do not wait for completion).
3. Now right-click any remote file, directory, or session and select **Custom Commands ➔ Open in Windows Terminal**.

---

## 📖 WinSCP Macros Cheat Sheet

WinSCP substitutes runtime parameters dynamically using macro variables:

| Macro | Meaning | Example Expansion |
| :---: | :--- | :--- |
| `!u` | Remote username of current session | `oracle` |
| `!@` | Target remote host or IP address | `db-prod.internal.corp` |
| `!#` | Remote SSH port number | `22` (or custom e.g. `2222`) |
| `!k` | Private key path (`.ppk` or OpenSSH format) | `C:\Users\John\.ssh\id_rsa.ppk` |
| `!p` | Session password (or prompts if not saved) | `SecretPass123` *(redacted in logs)* |
| `!P` | Stored session password (if saved in WinSCP) | `SecretPass123` *(redacted in logs)* |
| `!N` | Saved session name in WinSCP | `Production Database Cluster` |
| `!/` | **Currently active remote directory path** | `/var/log/nginx/` or `/opt/app/` |
| `!s` | Full session URL | `sftp://oracle@10.0.0.1:22/` |

> [!TIP]
> **Automatic `cd` Navigation (`!/`)**:
> Passing `--remote-dir "!/"` enables seamless folder matching. Whatever remote directory is currently open in WinSCP will be the directory your terminal immediately `cd`s into upon connection!

---

## 🛠️ Configuration Guide (`config.json5`)

The launcher reads configuration from `config.json5` (or `config.json`). JSON5 allows inline comments (`//`, `/* */`), unquoted keys, and trailing commas.

### 1. Global Settings

```json5
{
  // Terminal emulator: "windows_terminal", "wezterm", "alacritty", "conemu", "cmd", "custom"
  "terminal": "windows_terminal",

  // SSH backend: "wsl" (default) or "native" (Windows OpenSSH ssh.exe)
  "backend": "wsl",

  // WSL distribution name (optional; null uses default WSL distro)
  "wsl_distro": "Ubuntu",

  // Windows Terminal profile name (e.g. "Ubuntu", "PowerShell", "Command Prompt")
  "wt_profile": "Ubuntu",

  // Window placement mode: "tab" (new tab in existing window) or "window" (new window)
  "window_mode": "tab",

  // Prompt detection regex for automated startup sequence (jump host, su -, cd)
  "start_prompt_regex": "^(?:\\[[^\\]\\r\\n]+\\]|[^\\r\\n]*@[^\\r\\n]+(?::[^\\r\\n]*)?)\\s*[#$]\\s*$",

  // Global SSH options applied to all connections
  "ssh_extra_opts": [
    "-o", "ServerAliveInterval=60",
    "-o", "ServerAliveCountMax=3"
  ]
}
```

---

### 2. Profile Inheritance & Overrides

When managing multiple servers, servers often share common gateway architectures (e.g. a shared corporate bastion) while requiring different target accounts or directories.

With **Profile Inheritance**, you can define a base profile once and extend it using `"parent"` or `"extends"`:

```json5
{
  "profiles": {
    // -------------------------------------------------------------
    // Base Profile: Common corporate bastion & keepalive settings
    // -------------------------------------------------------------
    "corp-bastion": {
      "jump_command": "ssh bastion.company.com",
      "ssh_extra_opts": ["-o", "ServerAliveInterval=30"],
      "backend": "wsl",
      "wsl_distro": "Ubuntu"
    },

    // -------------------------------------------------------------
    // Child Profile 1: Inherits corp-bastion, switches to 'oracle'
    // -------------------------------------------------------------
    "prod-oracle": {
      "parent": "corp-bastion",
      "change_user": "oracle",
      "ssh_extra_opts": ["-o", "StrictHostKeyChecking=no"]
    },

    // -------------------------------------------------------------
    // Child Profile 2: Inherits corp-bastion, switches to 'postgres'
    // -------------------------------------------------------------
    "prod-postgres": {
      "parent": "corp-bastion",
      "change_user": "postgres",
      "start_commands": [
        "export PGDATA=/var/lib/postgresql/data",
        "psql -U postgres"
      ]
    },

    // -------------------------------------------------------------
    // Multi-Level Child (Grandchild): Inherits prod-oracle
    // -------------------------------------------------------------
    "prod-oracle-reports": {
      "parent": "prod-oracle",
      "start_directory": "/u01/app/oracle/reports/logs"
    },

    // -------------------------------------------------------------
    // Multiple Inheritance: Inherits multiple base profiles
    // -------------------------------------------------------------
    "secure-db": {
      "parent": ["corp-bastion", "audit-hooks"],
      "change_user": "secadmin"
    }
  }
}
```

#### How Inheritance Merging Works:
- **Scalar Properties**: `jump_command`, `change_user`, `start_directory`, `terminal`, `backend`, `wsl_distro`, and `wt_profile` defined in a child profile **override** values from parent profiles.
- **List Properties**: `ssh_extra_opts`, `start_commands`, and `pre_hooks` are **concatenated** in logical execution order (parent items first, followed by child items).
- **Cycle Safety**: Any circular dependency (e.g. `ProfileA -> ProfileB -> ProfileA`) is automatically caught and fails safely with an informative error message.

---

### 3. Wildcard Rules Engine

Eliminate the need to define individual sessions for hundreds of machines. Match hostnames or WinSCP session names with wildcards (`*`, `?`):

```json5
{
  "rules": [
    // All production machines in internal company network use the prod-oracle profile
    {
      "host": "*.prod.company.local",
      "profile": "prod-oracle"
    },

    // Any server in the 10.20.x.x private subnet switches to root directly
    {
      "host": "10.20.*",
      "change_user": "root"
    },

    // Any WinSCP session prefixed with 'AWS-'
    {
      "session": "AWS-*",
      "jump_command": "ssh aws-gateway.internal"
    }
  ]
}
```

---

### 4. Session Overrides & Pipeline Shorthand

For specific servers, override properties directly or use compact inline pipelines:

```json5
{
  "sessions": {
    // Shorthand 1: Reference a profile directly
    "Database-01": "prod-oracle",

    // Shorthand 2: Inline pipeline (jump host -> user switch -> initial directory)
    "Legacy-WebServer": "ssh old-jump.corp.net | su - apache | cd /var/log/httpd",

    // Full dictionary: Extend a profile and override specific keys
    "Custom-Analytics": {
      "profile": "prod-oracle",
      "change_user": "bi_developer",
      "start_directory": "/opt/bi/reports"
    }
  }
}
```

---

## 🖥️ Supported Terminal Emulators

| Terminal | `terminal` Key | Windows Terminal Tab Support | Features & Details |
| :--- | :---: | :---: | :--- |
| **Windows Terminal** | `"windows_terminal"` | ✅ Yes (`-w 0 new-tab`) | Native tab integration, profile selection (`wt_profile`), custom titles. |
| **WezTerm** | `"wezterm"` | Standalone window | Cross-platform GPU-accelerated terminal via `wezterm start`. |
| **Alacritty** | `"alacritty"` | Standalone window | Fast OpenGL terminal executed via `alacritty -e`. |
| **ConEmu** | `"conemu"` | Standalone window | Supports tabs via ConEmu's GUI engine (`ConEmu64.exe -run`). |
| **Standard CMD** | `"cmd"` | Windows Console | Built-in Windows Command Prompt console window. |
| **Custom Terminal** | `"custom"` | Dependent on tool | Custom array format with `{title}` and `{controller_cmd}` placeholders. |

### Custom Terminal Configuration Example
```json5
{
  "terminal": "custom",
  "terminal_command": [
    "C:\\Tools\\MyTerminal\\myterm.exe",
    "--title", "{title}",
    "-e", "{controller_cmd}"
  ]
}
```

---

## 🔒 SSH Execution Backends (WSL vs Native)

| Capability | WSL Backend (`"wsl"`) | Native Backend (`"native"`) |
| :--- | :---: | :---: |
| **Target SSH Client** | Linux OpenSSH (`/usr/bin/ssh`) | Windows OpenSSH (`ssh.exe`) |
| **Automatic PuTTY `.ppk` Conversion** | ✅ Yes (via `puttygen` in WSL) | ❌ Requires manual OpenSSH key |
| **Password Authentication (`sshpass`)** | ✅ Seamlessly supported | ⚠️ Restricted on Windows |
| **Corporate Windows Restrictions** | ✅ Works even if Windows SSH is blocked | ❌ Blocked if OpenSSH is disabled |
| **Custom WSL Distro Selection** | ✅ Yes (`wsl_distro: "OracleLinux8"`) | N/A |

---

## 💻 CLI Reference & PuTTY Compatibility

WinSCP Launcher accepts both traditional PuTTY arguments and standard GNU/POSIX-style options:

```
USAGE:
  1. WinSCP PuTTY Drop-In Mode:
     launcher.cmd -ssh -P <port> -i <key.ppk> [-pw <password>] user@host

  2. WinSCP Custom Commands Mode (with macros):
     launcher.cmd --user "!u" --host "!@" --port "!#" --key "!k" --session "!N" --remote-dir "!/"

  3. Standalone CLI:
     runner.py --user <user> --host <host> [options]

OPTIONS:
  -u, --user <username>       SSH remote username
  -H, --host <hostname>       SSH remote hostname or IP address
  -p, --port <port>           SSH remote port (default: 22)
  -k, --key <path>            Path to private key (.ppk, .pem, or OpenSSH format)
  -w, --password <pwd>        SSH password (automatically redacted in logs)
  -s, --session <name>        WinSCP session name or profile key
  -d, --remote-dir <path>     Remote directory for auto-cd navigation
  --terminal <type>           Override terminal emulator (windows_terminal, wezterm, etc.)
  --backend <type>            Override SSH backend (wsl, native)
  --doctor                    Run full system diagnostics and dependency checks
  -h, --help                  Display usage help and exit

PUTTY COMPATIBILITY FLAGS:
  -ssh                        Indicates SSH protocol (ignored, always SSH)
  -P <port>                   SSH port specification
  -i <key>                    Private key file
  -pw <password>              SSH password authentication
  -load <session>             Load session name
  -l <user>                   Remote user
```

---

## 🛡️ Security, Privacy & Credential Redaction

- **Automatic Password Redaction**: Passwords supplied via command line or injected into `sshpass` are filtered before output is written to disk. Log entries display `***REDACTED***` in place of sensitive credentials.
- **Git Safety**: `config.json5`, `config.json`, private keys, and session logs inside `logs/` are strictly ignored by `.gitignore`. You never have to worry about accidentally pushing internal enterprise hosts or IP addresses to version control.
- **Isolated Windows PTY**: Commands injected during startup (`su -`, `cd`) occur directly inside the private ConPTY stream without echoing raw strings to external window managers.

---

## 🩺 Diagnostics & Health Check (`--doctor`)

Verify your environment anytime by running the built-in diagnostic tool:

```cmd
python runner.py --doctor
```

The diagnostic tool automatically verifies:
1. **Operating System**: Checks for Windows host environment and build compatibility.
2. **Python Version**: Confirms Python 3.9+ runtime.
3. **Dependencies**: Validates `json5` library installation.
4. **Configuration Syntax**: Verifies `config.json5` validity, counts active rules/profiles, and **checks profile inheritance hierarchies for circular dependencies**.
5. **Terminal Emulator**: Tests if the configured terminal binary is executable in your `PATH`.
6. **Backend Tools**: In WSL mode, confirms `wsl.exe`, `ssh`, `puttygen`, and `sshpass` availability inside the target distribution.

---

## ❓ Troubleshooting & FAQ

<details>
<summary><b>Q: Startup commands (jump, su -, cd) are not being typed into the shell.</b></summary>
<br>
The ConPTY controller waits for the remote shell prompt to appear before transmitting startup commands. If your remote machine uses a non-standard prompt (e.g. customized zsh theme or colored prompt), the default regex may not match.
<br><br>
You can adjust <code>start_prompt_regex</code> in <code>config.json5</code> to match your shell's ending character (e.g. <code>.*[$#>]\\s*$</code>). Check <code>logs/winscp-launcher.debug.log</code> to inspect prompt detection logs.
</details>

<details>
<summary><b>Q: Windows Terminal creates a new window instead of opening a tab.</b></summary>
<br>
Ensure <code>"window_mode": "tab"</code> is set in <code>config.json5</code>. This passes <code>-w 0</code> to Windows Terminal (<code>wt.exe</code>), instructing it to attach to the most recently focused window. Also ensure your Windows Terminal version is up to date.
</details>

<details>
<summary><b>Q: How do I use my SSH key without converting it from .ppk?</b></summary>
<br>
If you use the <code>wsl</code> backend, WinSCP Launcher converts <code>.ppk</code> keys to OpenSSH format in a temporary WSL RAM cache on the fly using <code>puttygen</code>. You don't have to convert anything manually!
</details>

<details>
<summary><b>Q: How can I debug connection or parsing errors?</b></summary>
<br>
Detailed logs are written to:
<ul>
  <li><code>logs/winscp-launcher.log</code>: High-level session connection logs.</li>
  <li><code>logs/winscp-launcher.debug.log</code>: Detailed diagnostic and PTY state traces.</li>
  <li><code>logs/ssh/</code>: Per-session SSH output transcripts.</li>
</ul>
</details>

---

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
Before committing changes, ensure tests pass and code quality conforms to the project standards:

```bash
# Format and lint with Ruff
ruff check . --fix
ruff format .

# Type checking with Mypy
mypy winscp_launcher runner.py

# Run test suite
pytest
```

---

## 📄 License

Distributed under the **MIT License**. Feel free to use, modify, and distribute this software in personal and corporate environments alike.
