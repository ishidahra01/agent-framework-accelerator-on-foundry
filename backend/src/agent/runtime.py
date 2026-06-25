"""Microsoft Agent Framework runtime construction (Claude-free).

This module builds the Azure Resource Analyzer as a Microsoft Agent Framework
``Agent`` backed by a ``FoundryChatClient`` (Microsoft Foundry models). It binds
the explicit tools, the internal skills, and the composed system instructions.

API/SDK dependencies (verified against microsoft/agent-framework, Python):
* ``agent_framework.Agent`` + ``agent_framework.foundry.FoundryChatClient``
  (package ``agent-framework-foundry``, GA).
* Skills via ``agent_framework.SkillsProvider`` are an **experimental** MAF
  feature and may change before GA; we fall back to prompt-injected skills.

Microsoft Agent Framework imports are performed lazily inside the build functions
so configuration and instruction composition stay importable and testable in
environments where the framework is not installed.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .instructions import (
    compose_system_instructions,
    coordinator_instructions,
    load_agent_definitions,
    default_agents_root,
)
from .skills import (
    SkillRegistry,
    build_skills_provider,
    default_skills_root,
)
from .tools import build_default_tools
from .workspace import ensure_workspace_root, workspace_instructions

LOGGER = logging.getLogger("azure_resource_analyzer.runtime")

DEFAULT_AGENT_NAME = "azure-resource-analyzer"
_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RuntimeConfig:
    """Resolved configuration for the MAF runtime."""

    project_endpoint: str
    model_deployment: str
    agent_name: str
    agent_version: str
    enable_shell: bool


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUTHY


def resolve_agent_name() -> str:
    return os.getenv("FOUNDRY_AGENT_NAME") or DEFAULT_AGENT_NAME


def resolve_agent_version() -> str:
    return os.getenv("FOUNDRY_AGENT_VERSION", "")


def resolve_project_endpoint() -> str | None:
    return os.getenv("FOUNDRY_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT")


def resolve_model_deployment() -> str | None:
    return os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.getenv("FOUNDRY_MODEL_DEPLOYMENT")


def load_runtime_config() -> RuntimeConfig:
    """Resolve and validate runtime configuration from the environment.

    Raises ``RuntimeError`` with an actionable message when required Foundry
    configuration is missing.
    """

    endpoint = resolve_project_endpoint()
    if not endpoint:
        raise RuntimeError(
            "Microsoft Foundry is not configured. Set FOUNDRY_PROJECT_ENDPOINT "
            "(or AZURE_AI_PROJECT_ENDPOINT) to your Foundry project endpoint."
        )

    model = resolve_model_deployment()
    if not model:
        raise RuntimeError(
            "No model deployment configured. Set AZURE_AI_MODEL_DEPLOYMENT_NAME "
            "(or FOUNDRY_MODEL_DEPLOYMENT) to your Foundry model deployment name."
        )

    return RuntimeConfig(
        project_endpoint=endpoint,
        model_deployment=model,
        agent_name=resolve_agent_name(),
        agent_version=resolve_agent_version(),
        enable_shell=_flag("AGENT_ENABLE_SHELL_TOOL", default=False),
    )


def build_skill_registry(project_root: Path) -> SkillRegistry:
    return SkillRegistry.from_directory(default_skills_root(project_root))


def compose_runtime_instructions(
    project_root: Path,
    workspace_root: Path,
    *,
    registry: SkillRegistry | None = None,
    include_skill_catalog: bool = True,
) -> str:
    """Compose the runtime system prompt from definitions, skills, and contract."""

    definitions = load_agent_definitions(default_agents_root(project_root))
    coordinator = coordinator_instructions(definitions)
    registry = registry if registry is not None else build_skill_registry(project_root)
    skills_catalog = registry.advertisement() if include_skill_catalog else ""
    return compose_system_instructions(
        coordinator=coordinator,
        skills_catalog=skills_catalog,
        workspace_instructions=workspace_instructions(workspace_root),
        include_contract=True,
    )


def build_chat_client(config: RuntimeConfig) -> Any:
    """Create a Foundry chat client. Lazy-imports agent-framework-foundry."""

    try:
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover - requires MAF not installed
        raise RuntimeError(
            "agent-framework-foundry is not installed. Install it with "
            "'pip install agent-framework-foundry'."
        ) from exc

    return FoundryChatClient(
        project_endpoint=config.project_endpoint,
        model=config.model_deployment,
        credential=DefaultAzureCredential(),
    )


def build_agent(
    config: RuntimeConfig,
    *,
    project_root: Path,
    workspace_root: Path,
    client: Any | None = None,
) -> Any:
    """Build the single-coordinator MAF Agent with tools and skills.

    Lazy-imports ``agent_framework.Agent``. ``client`` may be injected for tests.
    """

    try:
        from agent_framework import Agent
    except ImportError as exc:  # pragma: no cover - requires MAF not installed
        raise RuntimeError(
            "agent-framework-core is not installed. Install the runtime with "
            "'pip install agent-framework-foundry agent-framework-foundry-hosting --pre'."
        ) from exc

    registry = build_skill_registry(project_root)
    skills_provider = build_skills_provider(default_skills_root(project_root))
    instructions = compose_runtime_instructions(
        project_root,
        workspace_root,
        registry=registry,
        # When a native SkillsProvider is active, skip the prompt catalog to avoid
        # duplicating skill advertisements.
        include_skill_catalog=skills_provider is None,
    )
    tools = build_default_tools(
        project_root=project_root,
        workspace_root=workspace_root,
        enable_shell=config.enable_shell,
    )

    agent_kwargs: dict[str, Any] = {
        "client": client or build_chat_client(config),
        "name": config.agent_name,
        "instructions": instructions,
        "tools": tools,
    }
    if skills_provider is not None:
        agent_kwargs["context_providers"] = [skills_provider]

    LOGGER.info(
        "Built MAF agent name=%s tools=%d skills_provider=%s",
        config.agent_name,
        len(tools),
        skills_provider is not None,
    )
    return Agent(**agent_kwargs)
