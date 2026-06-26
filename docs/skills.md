# Internal Skills

Skills are progressive-context playbooks that the agent can pull in when a task matches. In this accelerator they are **application runtime assets**, not GitHub Copilot repository customization files, and they are not the same thing as GitHub Copilot skills.

## Layout

Each skill lives in its own directory under `backend/skills/` with a `SKILL.md` file:

```text
backend/skills/
  azure-export-exploration/SKILL.md
  azure-security-baselines/SKILL.md
  azure-cost-patterns/SKILL.md
  azure-waf-review/SKILL.md
  azure-analysis-synthesis/SKILL.md
```

Every `SKILL.md` starts with YAML frontmatter (`name` and `description`, optionally `tags`) followed by markdown instructions:

```markdown
---
name: azure-security-baselines
description: Use when reviewing Azure resources for public exposure, encryption, identity, and network controls.
---

# Azure security baselines
...guidance...
```

The `description` is what the model sees when deciding whether to load a skill, so it should clearly state *when* to use the skill.

## How skills are loaded

`backend/src/agent/skills/loader.py` parses the `SKILL.md` files into `Skill` objects and exposes two paths:

1. **MAF native (preferred)** — `build_skills_provider()` returns a `SkillsProvider` built with `SkillsProvider.from_paths(...)`. This uses MAF's experimental file-based skill discovery and is attached to the agent through `context_providers=[provider]`.
2. **Prompt fallback** — when `agent-framework-core` is unavailable or the experimental feature is off, the registry (`backend/src/agent/skills/registry.py`) injects skill advertisements directly into the system prompt via `prompt_blocks()` / `advertisement()`.

Either way the loader returns the same parsed skills, so the runtime starts cleanly with or without the experimental feature.

## Role Skills in Hosted Single Mode

Hosted deployments run the analyzer as one coordinator `Agent` with `SkillsProvider.from_paths(...)` attached through `context_providers`. Role separation is provided by the coordinator instructions plus these file-based skills:

| Skill | Role |
| --- | --- |
| `azure-export-exploration` | Inventory files, resource types, high-signal facts, and missing context before review. |
| `azure-security-baselines` | Review public exposure, encryption, identity, authentication, and network controls. |
| `azure-cost-patterns` | Review oversizing, always-on spend, premium tiers, and elasticity gaps. |
| `azure-waf-review` | Review reliability, operational readiness, observability, and Well-Architected fit. |
| `azure-analysis-synthesis` | Merge evidence into the stable `summary` / `security` / `cost` / `architecture` contract. |

The older specialist agent markdown files under `backend/agents/` remain available for workflow-mode experiments, but Hosted Agent operation should treat the `SKILL.md` files as the standard role definitions.

## Experimental status

MAF Skills are gated behind `ExperimentalFeature.SKILLS` and emit a `FutureWarning`. The API may change before GA. The loader keeps the MAF bridge import-guarded and falls back to prompt injection so the accelerator does not break when the feature changes or is disabled.

## Adding a skill

1. Create `backend/skills/<skill-name>/SKILL.md` with `name`, `description`, and markdown body.
2. The loader discovers it automatically (skills are sorted by name for deterministic ordering).
3. Add or extend a test in `tests/test_skill_loader.py` if the skill encodes behaviour that should be validated.
