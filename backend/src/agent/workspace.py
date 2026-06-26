"""Hosted-agent workspace helper.

The workspace is the persistent filesystem boundary for the Hosted Agent demo:
normalized exports, intermediate summaries, and generated reports live there. It
must never store secrets or credential material.

Configuration uses ``AZURE_RESOURCE_ANALYZER_WORKSPACE_ROOT``. ``AGENT_WORKSPACE_ROOT``
and ``CLAUDE_WORKSPACE_ROOT`` are still honored as deprecated fallbacks during
migration and emit a warning.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

LOGGER = logging.getLogger("azure_resource_analyzer.workspace")

DEFAULT_WORKSPACE_ROOT_NAME = "work"
WORKSPACE_ROOT_ENV = "AZURE_RESOURCE_ANALYZER_WORKSPACE_ROOT"
_LEGACY_WORKSPACE_ROOT_ENV = "AGENT_WORKSPACE_ROOT"
_DEPRECATED_WORKSPACE_ROOT_ENV = "CLAUDE_WORKSPACE_ROOT"


def _configured_workspace_root() -> str | None:
    configured = os.getenv(WORKSPACE_ROOT_ENV)
    if configured:
        return configured

    legacy_agent = os.getenv(_LEGACY_WORKSPACE_ROOT_ENV)
    if legacy_agent:
        LOGGER.warning(
            "%s is deprecated for hosted deployments; use %s instead.",
            _LEGACY_WORKSPACE_ROOT_ENV,
            WORKSPACE_ROOT_ENV,
        )
        return legacy_agent

    legacy = os.getenv(_DEPRECATED_WORKSPACE_ROOT_ENV)
    if legacy:
        LOGGER.warning(
            "%s is deprecated; use %s instead.",
            _DEPRECATED_WORKSPACE_ROOT_ENV,
            WORKSPACE_ROOT_ENV,
        )
        return legacy
    return None


def resolve_workspace_root(project_root: Path) -> Path:
    """Resolve the workspace root from configuration or the default location."""

    configured = _configured_workspace_root()
    if configured:
        expanded = os.path.expandvars(configured)
        path = Path(expanded).expanduser()
        return path if path.is_absolute() else project_root / path

    return project_root / DEFAULT_WORKSPACE_ROOT_NAME


def ensure_workspace_root(project_root: Path) -> Path:
    """Resolve and create the workspace root."""

    workspace_root = resolve_workspace_root(project_root)
    workspace_root.mkdir(parents=True, exist_ok=True)
    return workspace_root


def workspace_instructions(workspace_root: Path) -> str:
    """Prompt fragment describing how the agent should use the workspace."""

    return f"""
Use the hosted-agent workspace root for generated artifacts and intermediate analysis files:
{workspace_root}

When a request includes a session, thread, or run identifier, keep request-specific files in a
subdirectory under that root. Treat this directory as the persistent filesystem boundary for the
Hosted Agent demo: normalized exports, intermediate summaries, and final reports belong there.
Do not write secrets or credential material to the workspace.
""".strip()
