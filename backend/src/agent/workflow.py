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
from typing import Any

from .contracts import analysis_output_instructions
from .instructions import (
    AgentDefinition,
    default_agents_root,
    load_agent_definitions,
    specialist_definitions,
)
from .runtime import RuntimeConfig, build_chat_client
from .skills import SkillRegistry, default_skills_root

LOGGER = logging.getLogger("azure_resource_analyzer.workflow")

SYNTHESIZER_NAME = "synthesize"


def _specialist_instructions(definition: AgentDefinition, registry: SkillRegistry) -> str:
    """Combine a specialist's instructions with its mapped skill playbooks."""

    parts = [definition.instructions.strip()]
    skill_block = registry.prompt_blocks(definition.skills) if definition.skills else ""
    if skill_block.strip():
        parts.append(skill_block.strip())
    return "\n\n".join(part for part in parts if part)


def _synthesizer_instructions() -> str:
    return (
        "You are the final synthesizer for an Azure resource analysis workflow. "
        "Merge the exploration, security, cost, and architecture findings into one "
        "coherent report. Respond in Japanese unless the user explicitly requests "
        "another language.\n\n" + analysis_output_instructions()
    )


def build_specialist_agents(
    config: RuntimeConfig,
    project_root: Path,
    *,
    client: Any | None = None,
) -> dict[str, Any]:
    """Construct the explore/security/cost/architecture/synthesize agents."""

    from agent_framework import Agent  # lazy

    chat_client = client or build_chat_client(config)
    registry = SkillRegistry.from_directory(default_skills_root(project_root))
    definitions = load_agent_definitions(default_agents_root(project_root))

    agents: dict[str, Any] = {}
    for definition in specialist_definitions(definitions):
        agents[definition.name] = Agent(
            client=chat_client,
            name=definition.name,
            instructions=_specialist_instructions(definition, registry),
        )

    agents[SYNTHESIZER_NAME] = Agent(
        client=chat_client,
        name=SYNTHESIZER_NAME,
        instructions=_synthesizer_instructions(),
    )
    return agents


def build_analysis_workflow_agent(
    config: RuntimeConfig,
    project_root: Path,
    *,
    client: Any | None = None,
) -> Any:
    """Build the specialist workflow and return it as a hostable agent."""

    try:
        from agent_framework import AgentExecutor, WorkflowBuilder
    except ImportError as exc:  # pragma: no cover - requires MAF not installed
        raise RuntimeError(
            "agent-framework-core is not installed. Install the runtime with "
            "'pip install agent-framework-foundry agent-framework-foundry-hosting --pre'."
        ) from exc

    agents = build_specialist_agents(config, project_root, client=client)

    explore = AgentExecutor(agents["explore"], context_mode="last_agent")
    security = AgentExecutor(agents["security"], context_mode="last_agent")
    cost = AgentExecutor(agents["cost"], context_mode="last_agent")
    architecture = AgentExecutor(agents["architecture"], context_mode="last_agent")
    synthesize = AgentExecutor(agents[SYNTHESIZER_NAME], context_mode="last_agent")

    workflow = (
        WorkflowBuilder(start_executor=explore, output_from=[synthesize])
        .add_edge(explore, security)
        .add_edge(explore, cost)
        .add_edge(explore, architecture)
        .add_edge(security, synthesize)
        .add_edge(cost, synthesize)
        .add_edge(architecture, synthesize)
        .build()
    )

    LOGGER.info("Built analysis workflow with %d specialist agents", len(agents))
    return workflow.as_agent()
