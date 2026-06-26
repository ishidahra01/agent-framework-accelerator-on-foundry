"""Specialist analysis flow implemented as a Microsoft Agent Framework workflow.

Re-implements the former Claude SubAgent decomposition without Claude. The flow
is:

    explore -> [security, cost, architecture] -> synthesize

``explore`` inventories the input, the three specialists review in parallel, and
``synthesize`` merges their findings into the stable output contract. The built
workflow is exposed as an agent via ``workflow.as_agent()`` so it can be hosted by
``ResponsesHostServer``.

Microsoft Agent Framework workflow APIs (``WorkflowBuilder``, ``AgentExecutor``)
are imported lazily so this module stays importable without the framework.

Reference: microsoft/agent-framework
``python/samples/04-hosting/foundry-hosted-agents/responses/05_workflows/main.py``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Sequence

from .contracts import analysis_output_instructions
from .instructions import (
    AgentDefinition,
    default_agents_root,
    load_agent_definitions,
    specialist_definitions,
)
from .runtime import RuntimeConfig, build_chat_client, structured_output_options
from .skills import SkillRegistry, default_skills_root
from .tools import build_default_tools

LOGGER = logging.getLogger("azure_resource_analyzer.workflow")

SYNTHESIZER_NAME = "synthesize"


def _response_text(response: Any) -> str:
    if hasattr(response, "with_text"):
        return str(response.with_text())
    agent_response = getattr(response, "agent_response", None)
    if agent_response is not None:
        text = getattr(agent_response, "text", None)
        if text:
            return str(text)
    return str(response)


def _merge_specialist_outputs(responses: Sequence[Any]) -> str:
    sections = []
    for response in responses:
        executor_id = getattr(response, "executor_id", "specialist")
        sections.append(f"## {executor_id}\n{_response_text(response)}")
    return "\n\n".join(sections)


def _specialist_instructions(definition: AgentDefinition, registry: SkillRegistry) -> str:
    """Combine a specialist's instructions with its mapped skill playbooks."""

    parts = [definition.instructions.strip()]
    skill_block = registry.prompt_blocks(definition.skills) if definition.skills else ""
    if skill_block.strip():
        parts.append(skill_block.strip())
    return "\n\n".join(part for part in parts if part)


def _synthesizer_instructions(optimizer_overlay: str = "") -> str:
    parts = [
        "You are the final synthesizer for an Azure resource analysis workflow. "
        "Merge the exploration, security, cost, and architecture findings into one "
        "coherent report. Respond in Japanese unless the user explicitly requests "
        "another language."
    ]
    if optimizer_overlay.strip():
        parts.append(optimizer_overlay.strip())
    parts.append(analysis_output_instructions())
    return "\n\n".join(parts)


def build_specialist_agents(
    config: RuntimeConfig,
    project_root: Path,
    workspace_root: Path,
    *,
    client: Any | None = None,
    optimizer_instructions: str = "",
) -> dict[str, Any]:
    """Construct the explore/security/cost/architecture/synthesize agents.

    The four investigative specialists receive the default read/search/export
    tools (bound to the project and workspace roots) so they can inspect Azure
    exports on disk, not only content already present in the conversation. The
    synthesizer is tool-free and instead enforces the structured output contract
    via ``response_format``.
    """

    from agent_framework import Agent  # lazy

    chat_client = client or build_chat_client(config)
    registry = SkillRegistry.from_directory(default_skills_root(project_root))
    definitions = load_agent_definitions(default_agents_root(project_root))
    specialist_tools = build_default_tools(
        project_root=project_root,
        workspace_root=workspace_root,
        enable_shell=config.enable_shell,
    )

    agents: dict[str, Any] = {}
    for definition in specialist_definitions(definitions):
        agents[definition.name] = Agent(
            client=chat_client,
            name=definition.name,
            instructions=_specialist_instructions(definition, registry),
            tools=specialist_tools,
            default_options={"store": False},
        )

    agents[SYNTHESIZER_NAME] = Agent(
        client=chat_client,
        name=SYNTHESIZER_NAME,
        instructions=_synthesizer_instructions(optimizer_instructions),
        default_options=structured_output_options(),
    )
    return agents


def build_analysis_workflow_agent(
    config: RuntimeConfig,
    project_root: Path,
    workspace_root: Path,
    *,
    client: Any | None = None,
    optimizer_instructions: str = "",
) -> Any:
    """Build the specialist workflow and return it as a hostable agent."""

    try:
        from agent_framework import (
            AgentExecutor,
            AgentExecutorResponse,
            FunctionExecutor,
            WorkflowBuilder,
        )
    except ImportError as exc:  # pragma: no cover - requires MAF not installed
        raise RuntimeError(
            "agent-framework-core is not installed. Install the runtime with "
            "'pip install agent-framework-foundry agent-framework-foundry-hosting --pre'."
        ) from exc

    agents = build_specialist_agents(
        config,
        project_root,
        workspace_root,
        client=client,
        optimizer_instructions=optimizer_instructions,
    )

    explore = AgentExecutor(agents["explore"], context_mode="last_agent")
    security = AgentExecutor(agents["security"], context_mode="last_agent")
    cost = AgentExecutor(agents["cost"], context_mode="last_agent")
    architecture = AgentExecutor(agents["architecture"], context_mode="last_agent")
    merge_findings = FunctionExecutor(
        _merge_specialist_outputs,
        id="merge_findings",
        input=list[AgentExecutorResponse],
        output=str,
    )
    synthesize = AgentExecutor(agents[SYNTHESIZER_NAME], context_mode="last_agent")

    # explore fans out to the three reviewers; the reviewers fan in to a single
    # merge step, then synthesize runs once with all three findings.
    workflow = (
        WorkflowBuilder(start_executor=explore, output_from=[synthesize])
        .add_edge(explore, security)
        .add_edge(explore, cost)
        .add_edge(explore, architecture)
        .add_fan_in_edges([security, cost, architecture], merge_findings)
        .add_edge(merge_findings, synthesize)
        .build()
    )

    LOGGER.info("Built analysis workflow with %d specialist agents", len(agents))
    return workflow.as_agent()
