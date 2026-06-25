"""Tests for the internal Skills loader and registry (PR2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.skills import (
    SkillLoadError,
    SkillRegistry,
    default_skills_root,
    load_skills,
    parse_skill_file,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
SKILLS_ROOT = BACKEND_DIR / "skills"
EXPECTED_SKILL_NAMES = {
    "azure-security-baselines",
    "azure-cost-patterns",
    "azure-waf-review",
}


def test_default_skills_root() -> None:
    assert default_skills_root(BACKEND_DIR) == SKILLS_ROOT


def test_load_bundled_skills() -> None:
    skills = load_skills(SKILLS_ROOT)
    names = {skill.name for skill in skills}
    assert names == EXPECTED_SKILL_NAMES
    for skill in skills:
        assert skill.description
        assert skill.instructions
        assert skill.path.name == "SKILL.md"


def test_skills_sorted_deterministically() -> None:
    skills = load_skills(SKILLS_ROOT)
    names = [skill.name for skill in skills]
    assert names == sorted(names)


def test_registry_lookup_and_catalog() -> None:
    registry = SkillRegistry.from_directory(SKILLS_ROOT)
    assert len(registry) == 3
    assert set(registry.names) == EXPECTED_SKILL_NAMES
    skill = registry.get("azure-security-baselines")
    assert skill is not None
    catalog = registry.advertisement()
    for name in EXPECTED_SKILL_NAMES:
        assert name in catalog


def test_registry_prompt_blocks_selection() -> None:
    registry = SkillRegistry.from_directory(SKILLS_ROOT)
    block = registry.prompt_blocks(["azure-cost-patterns"])
    assert "azure-cost-patterns" in block
    assert "azure-security-baselines" not in block


def test_missing_root_returns_empty(tmp_path: Path) -> None:
    assert load_skills(tmp_path / "does-not-exist") == []


def test_missing_frontmatter_raises(tmp_path: Path) -> None:
    skill_dir = tmp_path / "broken"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("no frontmatter here", encoding="utf-8")
    with pytest.raises(SkillLoadError):
        parse_skill_file(skill_file)


def test_missing_name_raises(tmp_path: Path) -> None:
    skill_dir = tmp_path / "noname"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\ndescription: something\n---\nbody",
        encoding="utf-8",
    )
    with pytest.raises(SkillLoadError):
        parse_skill_file(skill_file)
