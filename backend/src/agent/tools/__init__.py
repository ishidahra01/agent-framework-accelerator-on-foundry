"""Explicit MAF tools and guardrails for the Azure Resource Analyzer agent.

These tools recreate the capabilities previously provided by Claude built-in
tools (Read/Write/Glob/Grep/Bash) as explicit, root-constrained functions. The
runtime composes them with ``build_default_tools``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from .azure_export_tools import build_azure_export_tools, summarize_export
from .file_tools import build_file_tools
from .guardrails import (
    GuardrailError,
    ensure_command_allowed,
    ensure_readable,
    ensure_writable,
    is_denied_command,
    is_denied_path,
    resolve_within_root,
)
from .search_tools import build_search_tools
from .shell_tools import build_shell_tools

__all__ = [
    "GuardrailError",
    "build_azure_export_tools",
    "build_default_tools",
    "build_file_tools",
    "build_search_tools",
    "build_shell_tools",
    "ensure_command_allowed",
    "ensure_readable",
    "ensure_writable",
    "is_denied_command",
    "is_denied_path",
    "resolve_within_root",
    "summarize_export",
]


def build_default_tools(
    *,
    project_root: Path,
    workspace_root: Path,
    enable_shell: bool = False,
) -> list[Callable[..., str]]:
    """Assemble the default tool set bound to the project and workspace roots."""

    read_roots: Sequence[Path] = [Path(project_root), Path(workspace_root)]
    tools: list[Callable[..., str]] = []
    tools.extend(build_file_tools(read_roots=read_roots, workspace_root=workspace_root))
    tools.extend(build_search_tools(read_roots=read_roots))
    tools.extend(build_azure_export_tools(read_roots=read_roots))
    if enable_shell:
        tools.extend(build_shell_tools(cwd=project_root))
    return tools
