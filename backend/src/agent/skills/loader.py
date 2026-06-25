"""Loader for internal Skills stored as ``SKILL.md`` files.

Each skill lives in its own directory under the skills root and contains a
``SKILL.md`` file with YAML frontmatter (``name`` and ``description``) followed by
markdown instructions::

    backend/skills/
      azure-security-baselines/
        SKILL.md
      azure-cost-patterns/
        SKILL.md

This module parses those files into :class:`Skill` objects. It also provides an
optional bridge to the Microsoft Agent Framework native (experimental) Skills
system via :func:`build_skills_provider`, which is import-guarded so the loader
keeps working in environments where ``agent-framework-core`` is not installed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .models import Skill, SkillMetadata

LOGGER = logging.getLogger("azure_resource_analyzer.skills")

SKILL_FILENAME = "SKILL.md"
_FRONTMATTER_DELIMITER = "---"


class SkillLoadError(ValueError):
    """Raised when a ``SKILL.md`` file cannot be parsed."""


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    stripped = text.lstrip("\ufeff")
    if not stripped.startswith(_FRONTMATTER_DELIMITER):
        raise SkillLoadError("SKILL.md is missing the YAML frontmatter block.")

    # Drop the leading delimiter line, then split on the closing delimiter.
    after_open = stripped[len(_FRONTMATTER_DELIMITER):].lstrip("\r\n")
    end = after_open.find(f"\n{_FRONTMATTER_DELIMITER}")
    if end == -1:
        raise SkillLoadError("SKILL.md frontmatter block is not terminated.")

    frontmatter_text = after_open[:end]
    body = after_open[end + len(_FRONTMATTER_DELIMITER) + 1:]

    metadata = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(metadata, dict):
        raise SkillLoadError("SKILL.md frontmatter must be a YAML mapping.")

    return metadata, body.strip()


def _coerce_tags(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return ()


def parse_skill_file(path: Path) -> Skill:
    """Parse a single ``SKILL.md`` file into a :class:`Skill`."""

    raw = path.read_text(encoding="utf-8")
    metadata, body = _split_frontmatter(raw)

    name = str(metadata.get("name", "")).strip()
    description = str(metadata.get("description", "")).strip()
    if not name:
        raise SkillLoadError(f"Skill at {path} is missing a 'name'.")
    if not description:
        raise SkillLoadError(f"Skill '{name}' at {path} is missing a 'description'.")

    return Skill(
        metadata=SkillMetadata(
            name=name,
            description=description,
            tags=_coerce_tags(metadata.get("tags")),
        ),
        instructions=body,
        path=path,
    )


def load_skills(skills_root: Path) -> list[Skill]:
    """Discover and parse all ``SKILL.md`` files under ``skills_root``.

    Skills are returned sorted by name for deterministic ordering. Missing roots
    yield an empty list rather than raising, so the runtime can start without
    skills configured.
    """

    skills_root = Path(skills_root)
    if not skills_root.exists():
        LOGGER.warning("Skills root %s does not exist; no skills loaded.", skills_root)
        return []

    skills: list[Skill] = []
    for skill_file in sorted(skills_root.glob(f"*/{SKILL_FILENAME}")):
        skills.append(parse_skill_file(skill_file))

    LOGGER.info("Loaded %d skill(s) from %s", len(skills), skills_root)
    return skills


def build_skills_provider(skills_root: Path) -> Any | None:
    """Return a Microsoft Agent Framework ``SkillsProvider`` for ``skills_root``.

    Uses the MAF native (experimental) file-based skills discovery. Returns
    ``None`` when ``agent-framework-core`` is not installed or no skills exist, so
    callers can fall back to prompt-based inclusion.

    Note: MAF skills are an experimental feature (``ExperimentalFeature.SKILLS``)
    and may change before GA.
    """

    skills_root = Path(skills_root)
    if not skills_root.exists():
        return None

    try:
        from agent_framework import SkillsProvider  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - exercised only without MAF installed
        LOGGER.info(
            "agent-framework SkillsProvider unavailable; skills will be injected via prompt."
        )
        return None

    return SkillsProvider.from_paths(skill_paths=str(skills_root))
