"""Restricted shell execution tool.

Shell access is explicit and guarded: destructive/unapproved commands are denied,
execution is constrained to a working directory, and output is bounded by a
timeout and a maximum size. The runtime decides whether to expose this tool at
all (it is opt-in).
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

from .guardrails import (
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_SHELL_TIMEOUT_SECONDS,
    GuardrailError,
    ensure_command_allowed,
    truncate_output,
)

LOGGER = logging.getLogger("azure_resource_analyzer.tools.shell")


def build_shell_tools(
    *,
    cwd: Path,
    timeout_seconds: int = DEFAULT_SHELL_TIMEOUT_SECONDS,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> list[Callable[..., str]]:
    """Build a guarded ``run_shell_command`` tool bound to ``cwd``."""

    working_dir = Path(cwd).resolve()

    def run_shell_command(command: str) -> str:
        """Run a safe, read-only local shell command for lightweight inspection.

        Destructive commands (deletes, pushes, piping downloads to a shell, etc.)
        are blocked. Use this only for inspection and validation.

        Args:
            command: The shell command to execute.
        """

        ensure_command_allowed(command)
        LOGGER.info("run_shell_command %r (cwd=%s)", command, working_dir)
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise GuardrailError(
                f"Command timed out after {timeout_seconds}s: {command!r}"
            ) from exc

        output = completed.stdout
        if completed.stderr:
            output = f"{output}\n[stderr]\n{completed.stderr}"
        output = f"[exit {completed.returncode}]\n{output}"
        return truncate_output(output, max_output_bytes)

    return [run_shell_command]
