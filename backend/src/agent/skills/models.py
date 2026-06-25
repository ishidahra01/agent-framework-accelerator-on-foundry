"""Data models for the internal Skills system.

Skills here are *application runtime assets* for the Azure Resource Analyzer
agent. They are NOT GitHub Copilot Agent skills and are unrelated to any
repository-level Copilot customization. They are reusable Azure review playbooks
loaded explicitly by the agent runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SkillMetadata:
    """Frontmatter metadata parsed from a ``SKILL.md`` file."""

    name: str
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Skill:
    """A loaded skill: metadata plus its markdown instruction body."""

    metadata: SkillMetadata
    instructions: str
    path: Path

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def description(self) -> str:
        return self.metadata.description

    def advertisement(self) -> str:
        """One-line summary used for progressive disclosure in prompts."""

        return f"- {self.metadata.name}: {self.metadata.description}"

    def as_prompt_block(self) -> str:
        """Full skill content for explicit inclusion into a prompt or step."""

        return f"## Skill: {self.metadata.name}\n\n{self.instructions}".strip()
