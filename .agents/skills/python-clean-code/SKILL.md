---
name: python-clean-code
description: Enforce Python clean code, modern PEP 8 standards, Ruff linting, Mypy type-checking, and Pytest test suite execution.
---

# Python Clean Code Skill

Use this skill to inspect, lint, format, and ensure high code quality across the Python codebase.

## Workflow

1. **Format and Lint with Ruff**:
   ```bash
   ruff check . --fix
   ruff format .
   ```

2. **Static Type Checking with Mypy**:
   ```bash
   mypy winscp_launcher runner.py
   ```

3. **Run Unit Tests with Pytest**:
   ```bash
   pytest
   ```

## Best Practices
- Ensure all functions have type hints and docstrings.
- Catch specific exceptions rather than bare `except:`.
- Ensure sensitive data (passwords, base64 payloads) is redacted from logs.
- Keep classes and functions modular and loosely coupled.
