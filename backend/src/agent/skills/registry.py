"""Registry that holds loaded skills and exposes them to the runtime."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from .loader import load_skills
from .models import Skill


class SkillRegistry:
    """In-memory registry of internal skills keyed by name."""

    def __init__(self, skills: Iterable[Skill] | None = None) -> None:
        self._skills: dict[str, Skill] = {}
        for skill in skills or ():
            self.add(skill)

    @classmethod
    def from_directory(cls, skills_root: Path) -> "SkillRegistry":
        return cls(load_skills(skills_root))

    def add(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    @property
    def names(self) -> list[str]:
        return sorted(self._skills)

    def __len__(self) -> int:
        return len(self._skills)

    def __iter__(self) -> Iterator[Skill]:
        return iter(self._skills.values())

    def advertisement(self) -> str:
        """Render a compact catalog (name + description) for prompt injection.

        This supports progressive disclosure: the model first sees the catalog and
        can request full skill content only when relevant.
        """

        if not self._skills:
            return ""
        lines = ["Available internal skills (reusable Azure review playbooks):"]
        lines.extend(skill.advertisement() for skill in self)
        return "\n".join(lines)

    def prompt_blocks(self, names: Iterable[str] | None = None) -> str:
        """Render full instruction blocks for the given skills (all if None)."""

        selected = (
            [skill for skill in self if names is None or skill.name in set(names)]
        )
        return "\n\n".join(skill.as_prompt_block() for skill in selected)
