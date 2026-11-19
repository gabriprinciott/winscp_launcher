#!/usr/bin/env python3
"""Compatibility entry point for WinSCP and Windows Terminal."""

import sys

from winscp_launcher.cli import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Importing the logger here keeps startup failures visible in the
        # existing debug log while preserving the original exit behavior.
        from winscp_launcher.logging_config import log

        log.exception("Fatal error")
        sys.exit(1)
