"""Smoke tests for the MAF runtime and workflow construction (PR6).

These exercise configuration resolution and instruction composition (which need no
model access) and assert that the build entrypoints fail with an actionable error
when Microsoft Agent Framework is not installed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MAF_INSTALLED = importlib.util.find_spec("agent_framework") is not None
maf_absent_only = pytest.mark.skipif(
    MAF_INSTALLED,
    reason="Microsoft Agent Framework is installed; the import guard is not exercised. "
    "Construction is covered by tests/test_maf_construction.py.",
)

from src.agent.runtime import (
    DEFAULT_AGENT_NAME,
    build_agent,
    build_chat_client,
    build_skill_registry,
    compose_runtime_instructions,
    load_runtime_config,
    structured_output_options,
)
from src.agent.workflow import (
    _specialist_instructions,
    _synthesizer_instructions,
    build_analysis_workflow_agent,
)
from src.agent.instructions import load_agent_definitions, default_agents_root

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

FOUNDRY_ENV = (
    "FOUNDRY_PROJECT_ENDPOINT",
    "AZURE_AI_PROJECT_ENDPOINT",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME",
    "FOUNDRY_MODEL_DEPLOYMENT",
    "FOUNDRY_AGENT_NAME",
    "FOUNDRY_AGENT_VERSION",
    "AGENT_ENABLE_SHELL_TOOL",
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in FOUNDRY_ENV:
        monkeypatch.delenv(key, raising=False)


def _configure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example.services.ai.azure.com")
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")


def test_load_runtime_config_requires_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
    with pytest.raises(RuntimeError, match="FOUNDRY_PROJECT_ENDPOINT"):
        load_runtime_config()


def test_load_runtime_config_requires_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example")
    with pytest.raises(RuntimeError, match="model deployment"):
        load_runtime_config()


def test_load_runtime_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    config = load_runtime_config()
    assert config.model_deployment == "gpt-4o"
    assert config.agent_name == DEFAULT_AGENT_NAME
    assert config.enable_shell is False


def test_runtime_config_agent_name_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    monkeypatch.setenv("FOUNDRY_AGENT_NAME", "my-analyzer")
    monkeypatch.setenv("AGENT_ENABLE_SHELL_TOOL", "true")
    config = load_runtime_config()
    assert config.agent_name == "my-analyzer"
    assert config.enable_shell is True


def test_skill_registry_loaded() -> None:
    registry = build_skill_registry(BACKEND_DIR)
    assert len(registry) == 3


def test_compose_runtime_instructions(tmp_path: Path) -> None:
    text = compose_runtime_instructions(BACKEND_DIR, tmp_path / "work")
    for key in ("summary", "security", "cost", "architecture"):
        assert key in text
    # Skill catalog appears when no native SkillsProvider is active.
    assert "azure-security-baselines" in text
    assert "workspace" in text.lower()


def test_compose_runtime_instructions_with_optimizer_overlay(tmp_path: Path) -> None:
    overlay = "OPTIMIZER OVERLAY: prefer concise remediation steps."
    text = compose_runtime_instructions(
        BACKEND_DIR, tmp_path / "work", optimizer_overlay=overlay
    )
    assert overlay in text


def test_structured_output_options_uses_contract() -> None:
    from src.agent.contracts import AzureAnalysisResult

    options = structured_output_options()
    assert options["response_format"] is AzureAnalysisResult
    assert options["store"] is False


def test_specialist_instructions_include_skill(tmp_path: Path) -> None:
    definitions = load_agent_definitions(default_agents_root(BACKEND_DIR))
    registry = build_skill_registry(BACKEND_DIR)
    text = _specialist_instructions(definitions["security"], registry)
    assert "security reviewer" in text.lower()
    assert "azure-security-baselines" in text


def test_synthesizer_instructions_have_contract() -> None:
    text = _synthesizer_instructions()
    for key in ("summary", "security", "cost", "architecture"):
        assert key in text


def test_synthesizer_instructions_with_overlay() -> None:
    overlay = "OPTIMIZER OVERLAY: keep findings evidence-grounded."
    text = _synthesizer_instructions(overlay)
    assert overlay in text
    assert "summary" in text


@maf_absent_only
def test_build_chat_client_without_maf(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    config = load_runtime_config()
    with pytest.raises(RuntimeError, match="agent-framework-foundry"):
        build_chat_client(config)


@maf_absent_only
def test_build_agent_without_maf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _configure(monkeypatch)
    config = load_runtime_config()
    with pytest.raises(RuntimeError, match="agent-framework"):
        build_agent(config, project_root=BACKEND_DIR, workspace_root=tmp_path)


@maf_absent_only
def test_build_workflow_without_maf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _configure(monkeypatch)
    config = load_runtime_config()
    with pytest.raises(RuntimeError, match="agent-framework"):
        build_analysis_workflow_agent(config, BACKEND_DIR, tmp_path / "work")
