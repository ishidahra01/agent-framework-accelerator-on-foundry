# Architecture Overview

This repository is an Azure Well-Architected review agent accelerator built on the **Microsoft Agent Framework (MAF)** and hosted on **Microsoft Foundry**. The design target is a production lifecycle that can grow from Build and Host into Observe, Evaluate, Control, Optimize, and ROI.

The current implementation covers Part A, the harness layer that lets a MAF application run as a Microsoft Foundry Hosted Agent, and starts Part B with Observe and Evaluate foundations for accelerator-specific tracing context, policy checks, rubrics, and Foundry cloud evaluation handoff.

> Earlier revisions used the Claude Agent SDK as the inner harness. The runtime is now MAF-native and Claude-free; see [migration-from-claude-agent-sdk.md](migration-from-claude-agent-sdk.md).

## Two Harness Layers

The accelerator treats harness as two cooperating layers.

| Layer | Primary runtime | Responsibility | Current repository surface |
| --- | --- | --- | --- |
| Inner harness | Microsoft Agent Framework | Agent loop, explicit tools, specialist workflow, internal Skills, structured output | `backend/main.py`, `backend/src/agent/runtime.py`, `backend/src/agent/workflow.py`, `backend/agents/`, `backend/skills/` |
| Outer managed harness | Microsoft Foundry Hosted Agent | Hosted endpoint, sandbox, filesystem persistence, state boundary, telemetry bridge, identity, scale | `backend/agent.yaml`, `backend/.foundry/agent-metadata.yaml`, `docs/deploy-hosted-agent.md` |

MAF owns orchestration through `Agent` + `FoundryChatClient`. The Hosted Agent runtime exposes the agent through the responses protocol and connects it to Foundry operations.

## Runtime Flow

```text
User / client
  -> Foundry Hosted Agent responses endpoint
  -> backend/main.py (ResponsesHostServer)
  -> Microsoft Agent Framework runtime
  -> Agent + FoundryChatClient
  -> specialist workflow: explore -> security / cost / architecture -> synthesize
  -> internal Azure WAF / security / cost Skills
  -> guarded file / search / export / shell tools
  -> stable analysis output contract
  -> Part B observability attributes and traces
```

The runtime supports two modes via `AGENT_RUNTIME_MODE`:

- `workflow` (default): the coordinator delegates to specialist agents wired through `WorkflowBuilder` (`explore` first, then `security`/`cost`/`architecture`, then a synthesizer), exposed as a single agent with `workflow.as_agent()`.
- `single`: one coordinator agent with all tools and skills attached.

Source code, agent instructions, skills, and demo samples live under `backend/` so the hosted container has a self-contained project directory. Local generated artifacts can use `backend/work/`, while Hosted Agent deployment sets `AGENT_WORKSPACE_ROOT=$HOME/work` so generated files live in the session-persisted home filesystem.

## Internal Skills

Skills are MAF runtime assets, not GitHub Copilot customization files. They live under `backend/skills/<name>/SKILL.md` and are loaded through MAF's experimental `SkillsProvider` / `FileSkillsSource`. When the experimental Skills feature is unavailable, the loader falls back to injecting skill advertisements directly into the system prompt. See [skills.md](skills.md).

## Tools and Guardrails

Built-in capabilities are reimplemented as explicit MAF tools under `backend/src/agent/tools/`: file read/write, glob/grep search, Azure export loading, and an optional guarded shell tool. Guardrails deny access to secrets (`.env`, `secrets/**`), block path traversal outside the workspace, and reject destructive shell commands. See [security-model.md](security-model.md).

## Stable Output Contract

Azure analysis responses preserve these top-level keys:

```json
{
  "summary": { "resourcesAnalyzed": 25, "securityFindings": 12, "costSavingsOpportunities": 8 },
  "security": [ { "severity": "Critical", "resource": "...", "finding": "...", "remediation": "..." } ],
  "cost": [ { "resource": "...", "recommendation": "...", "estimatedSavings": "$15/month" } ],
  "architecture": [ { "pillar": "Operational Excellence", "finding": "...", "recommendation": "..." } ]
}
```

The contract is centralized as pydantic models in `backend/src/agent/contracts/azure_analysis.py` and appended to the runtime prompt. Part B uses it as the shared input for ASSERT policies, ACS output controls, rubric scoring, and ROI calculations.

## Part B Operational Loop

Part B keeps operational concerns outside the agent's reasoning prompts.

| Stage | Current or Planned Surface | Purpose |
| --- | --- | --- |
| Observe | `backend/src/agent/observability/tracing.py`, `backend/main.py`, Hosted Agent/App Insights traces | Attach agent identity, workspace, schema, and runtime context to traces. |
| Evaluate | `evals/`, `backend/src/agent/observability/evaluation.py`, `scripts/run_foundry_agent_eval.py` | Turn ASSERT-like policies and rubric criteria into repeatable local checks and optional Foundry cloud eval runs. |
| Control | Future `backend/control/acs.policy.yaml` and `acs_runtime.py` | Apply deterministic input, LLM, state, tool, and output controls. |
| Optimize | `backend/optimizer_configs/`, future trace-derived datasets | Identify changes that improve quality or reduce waste. |
| ROI | Future `roi.py` | Calculate completion rate, time saved, and cost efficiency. |

See [trust-roi-deepdive.md](trust-roi-deepdive.md) for the full Part B guide.

## Current Part A Status

| Capability | Status | Notes |
| --- | --- | --- |
| MAF agent loop | Implemented | `Agent` + `FoundryChatClient` constructed in `backend/src/agent/runtime.py`. |
| Specialist workflow | Implemented | Explore, security, cost, and architecture specialists wired in `backend/src/agent/workflow.py`. |
| Internal Skills | Implemented | Security, cost, and WAF guidance under `backend/skills/`, loaded via `SkillsProvider`. |
| Responses protocol entry | Implemented | `backend/agent.yaml` declares the hosted responses protocol. |
| Filesystem workspace contract | Implemented | Local `AGENT_WORKSPACE_ROOT=work`; Hosted Agent manifest uses `$HOME/work`. |
| Fixed analysis output schema | Implemented | `backend/src/agent/contracts/azure_analysis.py` centralizes the contract. |
| Tool guardrails | Implemented | Secret-path and destructive-command denylists in `backend/src/agent/tools/guardrails.py`. |
| Part B Observe helper | Implemented | `backend/src/agent/observability/tracing.py` defines common trace attributes and startup context. |
| Part B Evaluate helper | Implemented | `backend/src/agent/observability/evaluation.py` scores JSONL responses against ASSERT-like policy and rubric assets. |
| Approval checkpoint | Planned | Part B ACS will provide the policy layer. |
| Invocations protocol | Planned | Useful for batch JSON-in / JSON-out workflows after the responses path is stable. |

## Roadmap

1. Part A completion: add approval checkpoint behavior and optional Invocations support.
2. Part B foundation: expand request/run tracing, connect trace evaluation, add ACS policy/runtime, and ROI calculation helpers.
3. Demo hardening: add more sample exports, replayable scripts, and dashboard screenshots or setup notes.
