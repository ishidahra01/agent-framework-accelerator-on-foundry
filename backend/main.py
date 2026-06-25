"""Microsoft Foundry Hosted Agent entrypoint (Microsoft Agent Framework runtime).

This is the Claude-free runtime: it builds the Azure Resource Analyzer with
Microsoft Agent Framework and hosts it through the Foundry Hosted Agent responses
protocol.

Runtime modes (``AGENT_RUNTIME_MODE``):
* ``workflow`` (default): explore -> security/cost/architecture -> synthesize,
  built with ``WorkflowBuilder`` and hosted via ``workflow.as_agent()``.
* ``single``: one coordinator ``Agent`` with explicit tools and skills.

Note: ``agent-framework-foundry-hosting`` (``ResponsesHostServer``) is currently an
**alpha** package; install it with ``--pre``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from src.agent.observability.tracing import (
    configure_agent_framework_observability,
    create_observability,
    trace_server_startup,
)
from src.agent.optimization import load_agent_optimizer_config
from src.agent.runtime import (
    build_agent,
    load_runtime_config,
    resolve_agent_name,
    resolve_agent_version,
)
from src.agent.workflow import build_analysis_workflow_agent
from src.agent.workspace import ensure_workspace_root

PROJECT_ROOT = Path(__file__).resolve().parent
OPTIMIZER_CONFIG_DIR = PROJECT_ROOT / "optimizer_configs"
LOGGER = logging.getLogger("azure_resource_analyzer")
DEFAULT_PORT = 8088


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _configure_observability_environment() -> None:
    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        return
    connection_string = os.getenv("APPINSIGHTS_CONNECTION_STRING") or os.getenv(
        "AZURE_MONITOR_CONNECTION_STRING"
    )
    if connection_string:
        os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = connection_string


def _resolve_port(default: int = DEFAULT_PORT) -> int:
    raw = os.getenv("PORT")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        LOGGER.warning("Invalid PORT=%r. Falling back to %s.", raw, default)
        return default


def _resolve_runtime_mode() -> str:
    mode = os.getenv("AGENT_RUNTIME_MODE", "workflow").strip().lower()
    if mode not in {"workflow", "single"}:
        LOGGER.warning("Invalid AGENT_RUNTIME_MODE=%r. Falling back to 'workflow'.", mode)
        return "workflow"
    return mode


def _build_hosted_agent(workspace_root: Path, optimizer_instructions: str = ""):
    config = load_runtime_config()
    LOGGER.info(
        "Foundry endpoint=%s model=%s agent=%s",
        config.project_endpoint,
        config.model_deployment,
        config.agent_name,
    )
    mode = _resolve_runtime_mode()
    if mode == "single":
        return build_agent(
            config,
            project_root=PROJECT_ROOT,
            workspace_root=workspace_root,
            optimizer_instructions=optimizer_instructions,
        )
    return build_analysis_workflow_agent(
        config,
        PROJECT_ROOT,
        workspace_root,
        optimizer_instructions=optimizer_instructions,
    )


async def main() -> None:
    load_dotenv(override=False)
    _configure_observability_environment()
    _configure_logging()
    configure_agent_framework_observability(
        agent_name=resolve_agent_name(),
        agent_version=resolve_agent_version(),
    )

    optimizer_config = load_agent_optimizer_config(OPTIMIZER_CONFIG_DIR)
    LOGGER.info(
        "Agent optimizer config source=%s model=%s skills=%s enabled=%s",
        optimizer_config.source,
        optimizer_config.model or "<default>",
        optimizer_config.skill_count,
        optimizer_config.enabled,
    )

    workspace_root = ensure_workspace_root(PROJECT_ROOT)
    hosted_agent = _build_hosted_agent(workspace_root, optimizer_config.instructions)
    port = _resolve_port()

    observability = create_observability(
        agent_name=resolve_agent_name(),
        agent_version=resolve_agent_version(),
        workspace_root=workspace_root,
    )
    agent_id = getattr(hosted_agent, "id", resolve_agent_name())
    trace_server_startup(observability, agent_id=agent_id, port=port)

    from agent_framework_foundry_hosting import ResponsesHostServer

    LOGGER.info("Starting azure-resource-analyzer (mode=%s)", _resolve_runtime_mode())
    server = ResponsesHostServer(hosted_agent)
    await server.run_async()


if __name__ == "__main__":
    asyncio.run(main())
