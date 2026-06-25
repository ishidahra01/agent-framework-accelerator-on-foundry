"""Tests for the workspace helper (PR5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent import workspace as workspace_mod
from src.agent import workspaces as workspaces_shim
from src.agent.workspace import (
    DEFAULT_WORKSPACE_ROOT_NAME,
    ensure_workspace_root,
    resolve_workspace_root,
    workspace_instructions,
)

ENV_KEYS = ("AGENT_WORKSPACE_ROOT", "CLAUDE_WORKSPACE_ROOT")


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_default_workspace_root(tmp_path: Path) -> None:
    assert resolve_workspace_root(tmp_path) == tmp_path / DEFAULT_WORKSPACE_ROOT_NAME


def test_agent_workspace_root_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", "artifacts")
    assert resolve_workspace_root(tmp_path) == tmp_path / "artifacts"


def test_agent_workspace_root_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    abs_root = tmp_path / "abs"
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(abs_root))
    assert resolve_workspace_root(tmp_path) == abs_root


def test_legacy_claude_env_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_WORKSPACE_ROOT", "legacy")
    assert resolve_workspace_root(tmp_path) == tmp_path / "legacy"


def test_agent_env_takes_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", "primary")
    monkeypatch.setenv("CLAUDE_WORKSPACE_ROOT", "legacy")
    assert resolve_workspace_root(tmp_path) == tmp_path / "primary"


def test_ensure_workspace_root_creates(tmp_path: Path) -> None:
    root = ensure_workspace_root(tmp_path)
    assert root.exists() and root.is_dir()


def test_workspace_instructions_mentions_secrets(tmp_path: Path) -> None:
    text = workspace_instructions(tmp_path / "work")
    assert "secret" in text.lower()


def test_shim_reexports() -> None:
    assert workspaces_shim.resolve_workspace_root is workspace_mod.resolve_workspace_root
    assert workspaces_shim.ensure_workspace_root is workspace_mod.ensure_workspace_root
