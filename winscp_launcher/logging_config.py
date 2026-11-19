"""Logging setup for the launcher."""

import logging

from .config import DEBUG_LOG_FILE, LOG_FILE


def get_logger():
    logger = logging.getLogger("winscp-launcher")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")

        info_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)

        debug_handler = logging.FileHandler(DEBUG_LOG_FILE, encoding="utf-8")
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)

        logger.addHandler(info_handler)
        logger.addHandler(debug_handler)

    return logger


log = get_logger()
