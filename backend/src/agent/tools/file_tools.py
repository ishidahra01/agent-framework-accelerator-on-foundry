"""File access tools for the agent, constrained by guardrails.

These tools replace the Claude built-in ``Read``/``Write`` capabilities with
explicit, root-constrained functions. ``build_file_tools`` returns model-facing
callables (closures) that bind the allowed roots so the roots never appear in the
tool schema the model sees.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path

from .guardrails import (
    GuardrailError,
    ensure_readable,
    ensure_writable,
    truncate_output,
)

LOGGER = logging.getLogger("azure_resource_analyzer.tools.file")

MAX_READ_BYTES = 256 * 1024


def _read_within(read_roots: Sequence[Path], candidate: str) -> Path:
    last_error: GuardrailError | None = None
    for root in read_roots:
        try:
            return ensure_readable(root, candidate)
        except GuardrailError as exc:
            last_error = exc
    raise last_error or GuardrailError(f"No readable root for {candidate!r}.")


def build_file_tools(
    *,
    read_roots: Sequence[Path],
    workspace_root: Path,
) -> list[Callable[..., str]]:
    """Build read/write/list tools bound to the given roots."""

    resolved_read_roots = [Path(root).resolve() for root in read_roots]
    workspace = Path(workspace_root).resolve()

    def read_file(path: str) -> str:
        """Read a UTF-8 text file from the project or workspace.

        Args:
            path: File path, relative to the project root or absolute within it.
        """

        target = _read_within(resolved_read_roots, path)
        LOGGER.info("read_file %s", target)
        data = target.read_bytes()[:MAX_READ_BYTES]
        return truncate_output(data.decode("utf-8", errors="replace"), MAX_READ_BYTES)

    def list_files(directory: str = ".") -> str:
        """List files and folders under a directory in the project or workspace.

        Args:
            directory: Directory path relative to the project/workspace root.
        """

        target = _read_within(resolved_read_roots, directory)
        if not target.is_dir():
            raise GuardrailError(f"{target} is not a directory.")
        LOGGER.info("list_files %s", target)
        entries = sorted(
            f"{child.name}/" if child.is_dir() else child.name
            for child in target.iterdir()
        )
        return "\n".join(entries)

    def write_report(relative_path: str, content: str) -> str:
        """Write a generated report or artifact under the agent workspace.

        Args:
            relative_path: Destination path relative to the workspace root.
            content: UTF-8 text content to write.
        """

        target = ensure_writable(workspace, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        LOGGER.info("write_report %s (%d bytes)", target, len(content))
        return f"Wrote {len(content)} bytes to {target}"

    return [read_file, list_files, write_report]
