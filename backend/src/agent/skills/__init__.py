"""Internal Skills system for the Azure Resource Analyzer agent.

Skills are application runtime assets (reusable Azure review playbooks) loaded
explicitly by the agent runtime. They are NOT GitHub Copilot Agent skills.
"""

from __future__ import annotations

from pathlib import Path

from .loader import (
    SkillLoadError,
    build_skills_provider,
    load_skills,
    parse_skill_file,
)
from .models import Skill, SkillMetadata
from .registry import SkillRegistry

DEFAULT_SKILLS_DIRNAME = "skills"


def default_skills_root(project_root: Path) -> Path:
    """Canonical skills location: ``<project_root>/skills``."""

    return Path(project_root) / DEFAULT_SKILLS_DIRNAME


__all__ = [
    "DEFAULT_SKILLS_DIRNAME",
    "Skill",
    "SkillLoadError",
    "SkillMetadata",
    "SkillRegistry",
    "build_skills_provider",
    "default_skills_root",
    "load_skills",
    "parse_skill_file",
]
