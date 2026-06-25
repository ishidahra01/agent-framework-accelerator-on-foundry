"""Agent definitions and runtime instruction composition (Claude-free).

Agent definitions are Markdown files under ``backend/agents/`` with light YAML
frontmatter (``name``, ``description``, ``role``, optional ``skills``). The
coordinator definition drives the main system prompt; specialist definitions drive
the per-step instructions in the analysis workflow.

This module composes the runtime system instructions from:

* the coordinator definition (or a built-in fallback),
* the internal skills catalog (progressive disclosure),
* the workspace guidance, and
* the stable analysis output contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .contracts import analysis_output_instructions
from .markdown import parse_frontmatter

DEFAULT_AGENTS_DIRNAME = "agents"
COORDINATOR_NAME = "azure-resource-analyzer"
SPECIALIST_ORDER = ("explore", "security", "cost", "architecture")


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str
    instructions: str
    role: str = "specialist"
    skills: tuple[str, ...] = field(default_factory=tuple)


def default_agents_root(project_root: Path) -> Path:
    return Path(project_root) / DEFAULT_AGENTS_DIRNAME


def _coerce_skills(value: object) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return ()


def parse_agent_definition(path: Path) -> AgentDefinition:
    metadata, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    name = str(metadata.get("name", path.stem)).strip()
    description = str(metadata.get("description", "")).strip()
    role = str(metadata.get("role", "specialist")).strip() or "specialist"
    return AgentDefinition(
        name=name,
        description=description,
        instructions=body,
        role=role,
        skills=_coerce_skills(metadata.get("skills")),
    )


def load_agent_definitions(agents_root: Path) -> dict[str, AgentDefinition]:
    agents_root = Path(agents_root)
    definitions: dict[str, AgentDefinition] = {}
    if not agents_root.exists():
        return definitions
    for path in sorted(agents_root.glob("*.md")):
        definition = parse_agent_definition(path)
        definitions[definition.name] = definition
    return definitions


def default_coordinator_instructions() -> str:
    """Built-in fallback used when no coordinator definition is present."""

    return (
        "You are the main coordinator for an Azure resource analysis workflow, hosted behind "
        "Microsoft Agent Framework and Microsoft Foundry Hosted Agents. "
        "Respond in Japanese unless the user explicitly requests another language. "
        "For large or unfamiliar Azure exports, inventory the files and resources first, then run "
        "the security, cost, and architecture review steps and synthesize one coherent report. "
        "Prefer reading local workspace and sample files before any web lookup. Do not write secrets "
        "to the workspace."
    )


def coordinator_instructions(definitions: dict[str, AgentDefinition]) -> str:
    coordinator = definitions.get(COORDINATOR_NAME)
    if coordinator and coordinator.instructions:
        return coordinator.instructions
    return default_coordinator_instructions()


def specialist_definitions(definitions: dict[str, AgentDefinition]) -> list[AgentDefinition]:
    """Return specialist definitions in canonical workflow order."""

    ordered: list[AgentDefinition] = []
    for name in SPECIALIST_ORDER:
        definition = definitions.get(name)
        if definition is not None:
            ordered.append(definition)
    return ordered


def compose_system_instructions(
    *,
    coordinator: str,
    skills_catalog: str = "",
    workspace_instructions: str = "",
    optimizer_overlay: str = "",
    include_contract: bool = True,
) -> str:
    """Join the coordinator prompt with skills, workspace, and output contract.

    ``optimizer_overlay`` is the Agent Optimizer baseline/candidate instruction
    overlay. When present it is appended right after the coordinator prompt so the
    optimizer can steer behaviour without duplicating the long-lived constraints.
    """

    parts = [coordinator.strip()]
    if optimizer_overlay.strip():
        parts.append(optimizer_overlay.strip())
    if skills_catalog.strip():
        parts.append(skills_catalog.strip())
    if workspace_instructions.strip():
        parts.append(workspace_instructions.strip())
    if include_contract:
        parts.append(analysis_output_instructions())
    return "\n\n".join(part for part in parts if part)
