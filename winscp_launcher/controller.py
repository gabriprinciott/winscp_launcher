"""Entry point for the Windows Terminal ConPTY child process."""

import base64
import json
import re
import sys

from .config import DEFAULT_PROMPT_REGEX
from .conpty import ConPTYSession
from .logging_config import log


def controller_main(encoded_payload):
    try:
        raw = base64.urlsafe_b64decode(encoded_payload.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        command = payload["command"]
        startup_commands = payload.get("startup_commands")
        prompt_regex = payload.get("prompt_regex", DEFAULT_PROMPT_REGEX)

        if not isinstance(command, list) or not command:
            raise ValueError("Invalid controller command")
        if startup_commands is not None and (
            not isinstance(startup_commands, list)
            or not all(isinstance(item, str) and item for item in startup_commands)
        ):
            raise ValueError("Invalid startup commands")
        if not isinstance(prompt_regex, str) or not prompt_regex:
            raise ValueError("Invalid prompt regex")
        re.compile(prompt_regex)

        return ConPTYSession(
            command=command,
            startup_commands=startup_commands,
            prompt_regex=prompt_regex,
        ).run()
    except Exception:
        log.exception("Terminal controller failed")
        print(
            "\r\n[WinSCP launcher] Terminal controller error. See winscp-launcher.debug.log\r\n",
            file=sys.stderr,
            flush=True,
        )
        return 1
