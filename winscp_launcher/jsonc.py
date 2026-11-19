"""JSONC (JSON with comments) reader using the json5 library."""

from pathlib import Path
from typing import Any

try:
    import json5
except ImportError as exc:
    raise ImportError(
        "The 'json5' library is required to load configuration files.\n"
        "Please install project dependencies: pip install -r requirements.txt"
    ) from exc


def load_jsonc_file(path: Path | str) -> dict[str, Any]:
    """Read and parse a JSON / JSON5 / JSONC file."""
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = json5.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Configuration file {file_path} must contain a top-level JSON object")
    return data


def parse_jsonc_string(content: str) -> dict[str, Any]:
    """Parse a string containing JSON / JSON5 / JSONC."""
    data = json5.loads(content)
    if not isinstance(data, dict):
        raise ValueError("JSON string must contain a top-level JSON object")
    return data
