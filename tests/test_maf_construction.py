"""MAF-gated construction tests for the agent runtime and workflow.

These tests only run when Microsoft Agent Framework is installed (for example in
the Copilot cloud agent environment configured by
``.github/workflows/copilot-setup-steps.yml``). They exercise the real
``Agent``/``Workflow`` construction path with an injected fake chat client, so no
Foundry endpoint or network access is required. This verifies the wiring that the
unit tests cannot reach when MAF is absent:

* the four investigative specialists receive disk-access tools,
* the synthesizer (and single agent) enforce the structured-output contract,
* the Agent Optimizer overlay reaches the composed instructions,
* the workflow graph (explore -> fan-out -> fan-in -> synthesize) builds.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MAF_INSTALLED = importlib.util.find_spec("agent_framework") is not None

pytestmark = pytest.mark.skipif(
    not MAF_INSTALLED,
    reason="Microsoft Agent Framework is not installed; construction path cannot run.",
)

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


class _FakeChatClient:
    """Minimal stand-in for a MAF chat client.

    ``Agent`` stores the client without invoking it at construction time, so a
    plain object is sufficient to build the agent graph without a live model.
    """

    model = "fake-model"


@pytest.fixture(autouse=True)
def _configure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example.services.ai.azure.com")
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
    for key in ("FOUNDRY_AGENT_NAME", "FOUNDRY_AGENT_VERSION", "AGENT_ENABLE_SHELL_TOOL"):
        monkeypatch.delenv(key, raising=False)


def _config():
    from src.agent.runtime import load_runtime_config

    return load_runtime_config()


def test_structured_output_options_contract() -> None:
    from src.agent.contracts import AzureAnalysisResult
    from src.agent.runtime import structured_output_options

    options = structured_output_options()
    assert options["response_format"] is AzureAnalysisResult
    assert options["store"] is False


def test_build_single_agent_wiring() -> None:
    from src.agent.contracts import AzureAnalysisResult
    from src.agent.runtime import build_agent

    agent = build_agent(
        _config(),
        project_root=BACKEND_DIR,
        workspace_root=BACKEND_DIR,
        client=_FakeChatClient(),
        optimizer_instructions="OPTIMIZER_OVERLAY_MARKER",
    )

    assert agent is not None
    # Tools were attached so the single agent can read Azure exports from disk.
    assert agent.default_options.get("tools"), "single agent should have tools"
    # The structured-output contract is enforced via response_format.
    assert agent.default_options.get("response_format") is AzureAnalysisResult
    # The optimizer overlay reached the composed system instructions.
    assert "OPTIMIZER_OVERLAY_MARKER" in agent.default_options.get("instructions", "")


def test_build_specialist_agents_have_tools_and_contract() -> None:
    from src.agent.contracts import AzureAnalysisResult
    from src.agent.workflow import SYNTHESIZER_NAME, build_specialist_agents

    agents = build_specialist_agents(
        _config(),
        BACKEND_DIR,
        BACKEND_DIR,
        client=_FakeChatClient(),
        optimizer_instructions="SYNTH_OVERLAY_MARKER",
    )

    for name in ("explore", "security", "cost", "architecture", SYNTHESIZER_NAME):
        assert name in agents

    # The four investigative specialists carry disk-access tools (workflow mode
    # previously had none); the synthesizer is intentionally tool-free.
    for name in ("explore", "security", "cost", "architecture"):
        assert agents[name].default_options.get("tools"), f"{name} should have tools"
        assert agents[name].default_options.get("store") is False

    synthesizer = agents[SYNTHESIZER_NAME]
    assert synthesizer.default_options.get("response_format") is AzureAnalysisResult
    assert "SYNTH_OVERLAY_MARKER" in synthesizer.default_options.get("instructions", "")


def test_build_analysis_workflow_agent_builds() -> None:
    from src.agent.workflow import build_analysis_workflow_agent

    workflow_agent = build_analysis_workflow_agent(
        _config(),
        BACKEND_DIR,
        BACKEND_DIR,
        client=_FakeChatClient(),
    )

    # The fan-out/fan-in graph builds and is exposed as a hostable agent.
    assert workflow_agent is not None
