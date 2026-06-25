"""Backwards-compatible shim for the workspace helper.

The canonical helper now lives in ``src.agent.workspace``. This module re-exports
it so existing imports keep working during the migration. New code should import
from ``src.agent.workspace`` instead.
"""

from __future__ import annotations

from .workspace import (
    DEFAULT_WORKSPACE_ROOT_NAME,
    ensure_workspace_root,
    resolve_workspace_root,
    workspace_instructions,
)

__all__ = [
    "DEFAULT_WORKSPACE_ROOT_NAME",
    "ensure_workspace_root",
    "resolve_workspace_root",
    "workspace_instructions",
]
