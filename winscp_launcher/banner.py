"""ASCII Art banner and visual presentation for WinSCP Launcher."""

BANNER = r"""
 __      __.__             ____________________
/  \    /  \__| ____   ______ ____ _____\______   \
\   \/\/   /  |/    \ /  ___// ___\____ \|     ___/
 \        /|  |   |  \\___ \\  \___|  |_> >    |
  \__/\  / |__|___|  /____  >\___  >   __/|____|
       \/          \/     \/     \/|__|
       _
      | |    __ _ _   _ _ __   ___| |__   ___ _ __
      | |   / _` | | | | '_ \ / __| '_ \ / _ \ '__|
      | |__| (_| | |_| | | | | (__| | | |  __/ |
      |_____\__,_|\__,_|_| |_|\___|_| |_|\___|_|
"""

VERSION = "1.0.0"
SUBTITLE = "Smart Terminal & Jump Host Automation Bridge for WinSCP"


def get_banner_text(show_subtitle: bool = True) -> str:
    """Return the stylized ASCII banner."""
    lines = [BANNER.strip("\n")]
    if show_subtitle:
        lines.append(f"  v{VERSION} - {SUBTITLE}")
        lines.append("  " + "—" * 60)
    return "\n".join(lines)


def print_banner(show_subtitle: bool = True) -> None:
    """Print the stylized ASCII banner to standard output."""
    print(get_banner_text(show_subtitle))
