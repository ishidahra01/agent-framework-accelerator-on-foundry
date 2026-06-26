"""Tests for agent definitions and instruction composition (PR3)."""

from __future__ import annotations

from pathlib import Path

from src.agent.instructions import (
    COORDINATOR_NAME,
    SPECIALIST_ORDER,
    compose_system_instructions,
    coordinator_instructions,
    default_agents_root,
    load_agent_definitions,
    specialist_definitions,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
AGENTS_ROOT = BACKEND_DIR / "agents"


def test_default_agents_root() -> None:
    assert default_agents_root(BACKEND_DIR) == AGENTS_ROOT


def test_load_all_agent_definitions() -> None:
    definitions = load_agent_definitions(AGENTS_ROOT)
    expected = {COORDINATOR_NAME, *SPECIALIST_ORDER}
    assert expected.issubset(set(definitions))
    coordinator = definitions[COORDINATOR_NAME]
    assert coordinator.role == "coordinator"
    assert coordinator.instructions


def test_specialist_skill_mapping() -> None:
    definitions = load_agent_definitions(AGENTS_ROOT)
    assert definitions["security"].skills == ("azure-security-baselines",)
    assert definitions["cost"].skills == ("azure-cost-patterns",)
    assert definitions["architecture"].skills == ("azure-waf-review",)
    assert definitions["explore"].skills == ("azure-export-exploration",)


def test_specialist_definitions_ordered() -> None:
    definitions = load_agent_definitions(AGENTS_ROOT)
    ordered = specialist_definitions(definitions)
    assert [d.name for d in ordered] == list(SPECIALIST_ORDER)


def test_coordinator_instructions_from_file() -> None:
    definitions = load_agent_definitions(AGENTS_ROOT)
    text = coordinator_instructions(definitions)
    assert "coordinator" in text.lower()


def test_coordinator_instructions_fallback() -> None:
    text = coordinator_instructions({})
    assert "Microsoft Agent Framework" in text
    assert "Japanese" in text


def test_compose_includes_contract_and_skills() -> None:
    composed = compose_system_instructions(
        coordinator="COORD",
        skills_catalog="CATALOG",
        workspace_instructions="WORKSPACE",
        include_contract=True,
    )
    assert "COORD" in composed
    assert "CATALOG" in composed
    assert "WORKSPACE" in composed
    # Contract keys present.
    for key in ("summary", "security", "cost", "architecture"):
        assert key in composed


def test_compose_without_contract() -> None:
    composed = compose_system_instructions(coordinator="COORD", include_contract=False)
    assert composed == "COORD"
