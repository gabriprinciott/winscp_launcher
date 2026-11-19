"""Unit tests for JSONC / JSON5 configuration loader."""

try:
    import json5  # noqa: F401

    has_json5 = True
except ImportError:
    has_json5 = False


def test_parse_jsonc_string_with_comments():
    if not has_json5:
        print("Skipping json5 test: json5 not installed")
        return
    from winscp_launcher.jsonc import parse_jsonc_string

    raw = """
    {
      // Single line comment
      "terminal": "windows_terminal",
      /* Multi-line
         comment */
      "port": 2222, // Trailing comment
      "list": [1, 2, 3,], // Trailing comma supported
    }
    """
    data = parse_jsonc_string(raw)
    assert data["terminal"] == "windows_terminal"
    assert data["port"] == 2222
    assert data["list"] == [1, 2, 3]
