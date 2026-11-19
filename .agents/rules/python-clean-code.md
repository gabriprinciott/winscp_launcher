---
description: Python Clean Code, Typing, Architecture, and Formatting Standards
always_on: true
---

# Python Clean Code & Architecture Guidelines

When developing or refactoring Python code in this project, adhere strictly to the following standards:

## 1. Code Style & Standards
- Follow **PEP 8** naming conventions and formatting standards.
- Prefer **Python 3.10+** modern idioms (e.g., `str | None` instead of `Optional[str]`, `list[str]` instead of `typing.List[str]`).
- Keep functions small, focused, and compliant with the **Single Responsibility Principle (SRP)**.
- Function length should ideally not exceed 40-50 lines unless handling an intrinsically atomic mapping or state-machine.

## 2. Typing & Docstrings
- Use explicit type annotations for all function parameters, return values, and significant module attributes.
- Use `typing` / built-in generics (`dict[str, Any]`, `list[str]`, `Sequence[str]`, `Callable[..., Any]`).
- Write clear, concise docstrings following the Google or Sphinx style.
- Preserve and update existing docstrings and comments.

## 3. Architecture & Modularity
- Decouple layers: CLI parsing, configuration loading, session resolution, terminal launching, and process controller must be isolated in dedicated modules.
- Avoid circular imports.
- Minimize dependencies: use standard library where appropriate, but rely on specialized packages (like `json5`) when explicitly designed.
- Never write hardcoded credentials, paths, or secrets.

## 4. Error Handling & Robustness
- Never use bare `except:`. Always catch specific exceptions (`FileNotFoundError`, `ValueError`, `KeyError`, etc.).
- When catching generic `Exception` at entry points, log the stack trace using the project's logging facility (`log.exception(...)`).
- Fail gracefully with user-friendly error messages on CLI entry points, returning non-zero exit codes.

## 5. Security & Secrets Management
- Always redact passwords, tokens, and base64 payloads from log messages and console output.
- Validate and sanitize external input (hostnames, paths, user names) before using them in shell commands or file operations.
