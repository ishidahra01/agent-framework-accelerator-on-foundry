"""Security guardrails shared by the agent tools.

These guardrails enforce the minimum protections required by the migration:

* deny reading secret material (``.env``, ``.env.*``, ``secrets/**``),
* constrain filesystem access to approved roots (no path traversal),
* deny destructive or unapproved shell commands by default,
* apply timeouts and output-size limits to shell execution.
"""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_SHELL_TIMEOUT_SECONDS = 30
DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024

# Filenames / path segments that must never be read through agent tools.
_DENIED_BASENAMES = {".env"}
_DENIED_SEGMENTS = {"secrets"}

# Destructive or unapproved shell patterns, denied by default.
_DENIED_SHELL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brm\s+-[a-z]*r[a-z]*f",          # rm -rf / rm -fr
        r"\brm\s+-[a-z]*f[a-z]*r",
        r"\bgit\s+push\b",
        r"\b(curl|wget|iwr|invoke-webrequest)\b.*\|\s*(sh|bash|pwsh|powershell)\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r":\(\)\s*\{",                       # fork bomb
        r"\b(shutdown|reboot|halt|poweroff)\b",
        r"\bremove-item\b.*-recurse.*-force",
        r"\bdel\b\s+/[sqf]",
        r">\s*/dev/sd[a-z]",
    )
)


class GuardrailError(PermissionError):
    """Raised when a tool action is blocked by a guardrail."""


def is_denied_path(candidate: Path) -> bool:
    """Return True when ``candidate`` references denied secret material."""

    name = candidate.name.lower()
    if name in _DENIED_BASENAMES or name.startswith(".env."):
        return True
    return any(part.lower() in _DENIED_SEGMENTS for part in candidate.parts)


def resolve_within_root(root: Path, candidate: str | Path) -> Path:
    """Resolve ``candidate`` and ensure it stays within ``root``.

    ``candidate`` may be absolute or relative to ``root``. Raises
    :class:`GuardrailError` on path traversal outside the root.
    """

    root = Path(root).resolve()
    raw = Path(candidate)
    resolved = (raw if raw.is_absolute() else root / raw).resolve()
    if resolved != root and root not in resolved.parents:
        raise GuardrailError(f"Path {resolved} is outside the allowed root {root}.")
    return resolved


def ensure_readable(root: Path, candidate: str | Path) -> Path:
    """Resolve a read target within ``root`` and reject denied secret paths."""

    resolved = resolve_within_root(root, candidate)
    if is_denied_path(resolved):
        raise GuardrailError(f"Reading {resolved} is denied by the secret guardrail.")
    return resolved


def ensure_writable(root: Path, candidate: str | Path) -> Path:
    """Resolve a write target within ``root`` and reject denied secret paths."""

    resolved = resolve_within_root(root, candidate)
    if is_denied_path(resolved):
        raise GuardrailError(f"Writing {resolved} is denied by the secret guardrail.")
    return resolved


def is_denied_command(command: str) -> bool:
    """Return True when ``command`` matches a destructive/unapproved pattern."""

    return any(pattern.search(command) for pattern in _DENIED_SHELL_PATTERNS)


def ensure_command_allowed(command: str) -> None:
    """Raise :class:`GuardrailError` when ``command`` is denied."""

    if not command or not command.strip():
        raise GuardrailError("Empty shell command is not allowed.")
    if is_denied_command(command):
        raise GuardrailError(f"Shell command blocked by guardrail: {command!r}")


def truncate_output(text: str, max_bytes: int = DEFAULT_MAX_OUTPUT_BYTES) -> str:
    """Truncate ``text`` to ``max_bytes`` (UTF-8), appending a marker if cut."""

    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    clipped = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return clipped + "\n... [output truncated]"
