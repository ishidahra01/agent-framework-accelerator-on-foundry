# Migrating from the Claude Agent SDK build

Earlier revisions of this accelerator used the Claude Agent SDK as the inner harness, bridged to Foundry through `agent-framework-claude`. The runtime is now fully native to the **Microsoft Agent Framework (MAF)** and contains no Claude dependencies.

This document maps the old components to their MAF replacements so existing deployments can be updated.

## Why migrate

- Single framework: MAF owns the agent loop, tools, workflow orchestration, and structured output, so there is no second SDK to keep in sync.
- Foundry-native model access through `FoundryChatClient` instead of the Anthropic-on-Foundry bridge.
- No Anthropic API keys or model aliases to manage; authentication uses `DefaultAzureCredential`.

## Component mapping

| Concept | Old (Claude Agent SDK) | New (Microsoft Agent Framework) |
| --- | --- | --- |
| Agent loop | `ClaudeAgent` via `agent-framework-claude` | `Agent` + `FoundryChatClient` (`backend/src/agent/runtime.py`) |
| Model client | Anthropic-on-Foundry endpoint | `FoundryChatClient` from `agent_framework.foundry` |
| Main agent prompt | `backend/CLAUDE.md` | `backend/agents/azure-resource-analyzer.md` |
| SubAgents | `backend/.claude/agents/*.md` | Hosted mode uses `backend/skills/*/SKILL.md` role skills; `backend/agents/{explore,security,cost,architecture}.md` remains for workflow experiments |
| Specialist orchestration | Claude SubAgent delegation | Hosted default is one coordinator `Agent` with MAF Skills; optional workflow lives in `backend/src/agent/workflow.py` |
| Skills | `backend/.claude/skills/*/SKILL.md` | `backend/skills/*/SKILL.md` via `SkillsProvider.from_paths(...)` |
| Built-in tools | Claude Read/Write/Edit/Glob/Grep/Bash | Explicit MAF tools (`backend/src/agent/tools/`) |
| Output contract | `backend/src/agent/runtime_contracts.py` | `backend/src/agent/contracts/azure_analysis.py` (pydantic) |
| Workspace root | `CLAUDE_WORKSPACE_ROOT` | `AZURE_RESOURCE_ANALYZER_WORKSPACE_ROOT` |
| Optimizer config | `backend/.claude/optimizer_configs/` | `backend/optimizer_configs/` |
| Hosting | `ResponsesHostServer` | `ResponsesHostServer` (unchanged) |

## Environment variable mapping

| Old | New |
| --- | --- |
| `CLAUDE_CODE_USE_FOUNDRY` | (removed) |
| `ANTHROPIC_FOUNDRY_BASE_URL` / `ANTHROPIC_FOUNDRY_API_KEY` | (removed; use `DefaultAzureCredential`) |
| `ANTHROPIC_DEFAULT_*_MODEL` | `AZURE_AI_MODEL_DEPLOYMENT_NAME` |
| `AZURE_AI_PROJECT_ENDPOINT` | `AZURE_RESOURCE_ANALYZER_PROJECT_ENDPOINT` (also accepts `AZURE_AI_PROJECT_ENDPOINT`) |
| `CLAUDE_MODEL` / `CLAUDE_MAX_TURNS` / `CLAUDE_EFFORT` | (removed) |
| `CLAUDE_PERMISSION_MODE` | Tool guardrails (`backend/src/agent/tools/guardrails.py`) |
| `CLAUDE_WORKSPACE_ROOT` | `AZURE_RESOURCE_ANALYZER_WORKSPACE_ROOT` (old names still read as deprecated fallbacks) |
| `CLAUDE_CODE_USE_POWERSHELL_TOOL` | `AZURE_RESOURCE_ANALYZER_ENABLE_SHELL_TOOL` |

## Dependency changes

Removed from `backend/requirements.txt`:

- `agent-framework-claude`
- `claude-agent-sdk`

Added:

- `agent-framework-foundry` (provides `FoundryChatClient`)
- `azure-identity` (for `DefaultAzureCredential`)

`agent-framework-foundry-hosting` (Alpha) is still required for `ResponsesHostServer`.

## Behavioural notes

- The fixed JSON analysis contract is unchanged, so Part B observability, evaluation, and ROI assets continue to apply.
- Internal Skills use MAF's experimental Skills feature, which emits a `FutureWarning`. A plain-prompt fallback is used when the feature is unavailable. See [skills.md](skills.md).
- Default demo responses remain Japanese where the sample scenario calls for it.
