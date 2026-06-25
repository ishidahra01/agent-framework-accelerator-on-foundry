# Azure Resource Analyzer Accelerator on Foundry

This repository is a reference accelerator for building an Azure resource analysis agent with the **Microsoft Agent Framework (MAF)** and running it as a **Microsoft Foundry Hosted Agent**.

The sample scenario is an Azure Well-Architected review. The agent reads Azure exports, ARM-style JSON, or resource configuration snapshots, then returns security findings, cost recommendations, and architecture guidance through a stable output contract.

> **Migrating from the Claude Agent SDK build?** Earlier revisions of this accelerator used the Claude Agent SDK as the inner harness. The runtime is now fully MAF-native and Claude-free. See [docs/migration-from-claude-agent-sdk.md](docs/migration-from-claude-agent-sdk.md) for the mapping between the old and new components.

The current implementation covers **Part A: Harness Deep Dive** and the first steps of **Part B: Trust to ROI Deep Dive**. Part A shows how to build and host the agent on MAF. Part B includes Observe, Evaluate, and Optimize foundations: tracing context, local ASSERT-like policy checks, rubric scorecards, seed datasets, a Foundry portal Rubric evaluation guide, optional Foundry cloud evaluation automation, and Agent Optimizer readiness. Start with [docs/architecture.md](docs/architecture.md) for the runtime walkthrough and [docs/deploy-hosted-agent.md](docs/deploy-hosted-agent.md) for deployment.

## What This Repository Demonstrates

- Microsoft Agent Framework as the inner harness for the agent loop, specialist decomposition, internal Skills, explicit tools, and structured output
- `FoundryChatClient` as the model client for Foundry-hosted deployments
- A multi-specialist MAF workflow (explore → security / cost / architecture → synthesize) that can also run as a single coordinator agent
- An internal Skills system built on MAF's experimental `SkillsProvider` / `FileSkillsSource`, with a plain-prompt fallback
- Microsoft Foundry Hosted Agent as the outer managed harness for endpoint hosting, sandbox execution, state boundaries, telemetry, and future identity / guardrail integration
- A fixed Azure analysis output schema (pydantic) used by Part B for observability, evaluation, control, optimization, and ROI
- A Part B Observe foundation that adds accelerator-specific OpenTelemetry attributes around the Hosted Agent runtime
- A Part B Evaluate foundation that turns policies and rubrics into repeatable local checks, a portal-first Rubric evaluation flow, and optional Foundry cloud eval automation
- A Part B Optimize foundation that wires Agent Optimizer baseline/candidate config into the Hosted Agent runtime
- Tool guardrails that deny secret paths and destructive shell commands by default
- A deliberately weak Azure export under `backend/samples/bad-config/` for repeatable demos

## Current Architecture

```text
User / client
  -> Microsoft Foundry Hosted Agent responses endpoint
  -> backend/main.py (ResponsesHostServer)
  -> Microsoft Agent Framework runtime
  -> Agent + FoundryChatClient
  -> specialist workflow: explore -> security / cost / architecture -> synthesize
  -> internal Azure WAF / security / cost Skills
  -> guarded file / search / export / shell tools
  -> stable JSON analysis contract (pydantic)
```

The architecture is described in more detail in [docs/architecture.md](docs/architecture.md). The internal Skills system is documented in [docs/skills.md](docs/skills.md) and the tool guardrails in [docs/security-model.md](docs/security-model.md).

## Repository Layout

```text
backend/
  main.py                         # Hosted Agent entrypoint (ResponsesHostServer)
  agent.yaml                      # azd / Hosted Agent manifest
  agents/                         # MAF-neutral coordinator + specialist instructions
  skills/                         # Internal Azure WAF, security, and cost Skills (SKILL.md)
  optimizer_configs/              # Agent Optimizer baseline overlay
  src/agent/
    runtime.py                    # Agent + FoundryChatClient construction
    workflow.py                   # Specialist workflow (explore/security/cost/architecture/synthesize)
    instructions.py               # Loads agents/*.md and composes system instructions
    workspace.py                  # Hosted workspace root helper (AGENT_WORKSPACE_ROOT)
    contracts/azure_analysis.py   # Stable output schema (pydantic) and prompt contract
    skills/                       # Internal Skills loader/registry over SkillsProvider
    tools/                        # Guarded file/search/export/shell tools
    optimization.py               # Agent Optimizer runtime config bridge
    observability/tracing.py      # Part B Observe helper and trace attribute contract
    observability/evaluation.py   # Part B Evaluate local policy/rubric scorecard helper
  .foundry/
    agent-metadata.yaml           # Design metadata for Hosted Agent behavior
  samples/
    bad-config/azure-export.json  # Demo input included in the hosted container
evals/                            # Part B policy, rubric, conversation, and JSONL evaluation assets
scripts/
  run_foundry_agent_eval.py       # Optional Foundry cloud evaluation runner
docs/
  architecture.md
  migration-from-claude-agent-sdk.md
  skills.md
  security-model.md
  deploy-hosted-agent.md
  hosted-agent-test-plan.md
  harness-deepdive.md
  trust-roi-deepdive.md
  foundry-portal-rubric-evaluation.md
  foundry-agent-optimizer-concepts.md
  foundry-agent-optimizer.md
```

## Agent Design

The coordinator agent (`azure-resource-analyzer`) drives four specialists:

| Specialist | Responsibility |
| --- | --- |
| `explore` | Inventories files, resource types, and high-signal configuration facts before deeper review. |
| `security` | Reviews public exposure, encryption, identity, authentication, and network controls. |
| `cost` | Reviews oversized resources, always-on spend, premium SKUs, and elasticity gaps. |
| `architecture` | Reviews reliability, operational readiness, observability, and Well-Architected alignment. |

In `workflow` mode the specialists run as a MAF workflow; in `single` mode the coordinator runs as one agent with all tools and skills. Skills under `backend/skills/` provide progressive context loading for Azure WAF, security baselines, and cost patterns.

## Expected Analysis Output

Azure analysis preserves this contract:

```json
{
  "summary": { "resourcesAnalyzed": 25, "securityFindings": 12, "costSavingsOpportunities": 8 },
  "security": [ { "severity": "Critical", "resource": "...", "finding": "...", "remediation": "..." } ],
  "cost": [ { "resource": "...", "recommendation": "...", "estimatedSavings": "$15/month" } ],
  "architecture": [ { "pillar": "Operational Excellence", "finding": "...", "recommendation": "..." } ]
}
```

The contract is centralized in `backend/src/agent/contracts/azure_analysis.py` and appended to the runtime prompt in `backend/src/agent/runtime.py`.

## Local Development

From the repository root:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configure Foundry access through `backend/.env` or environment variables (see `backend/.env.example`):

```env
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<deployment-name>
AGENT_RUNTIME_MODE=workflow
AGENT_WORKSPACE_ROOT=work
```

Authentication uses `DefaultAzureCredential`: run `az login` locally, or rely on managed identity when deployed. No API keys are required.

For Hosted Agent deployment, the manifest sets `AGENT_WORKSPACE_ROOT=$HOME/work` so generated files are written under the session-persisted HOME filesystem that appears in the Foundry Portal Files view.

Start the local responses server:

```powershell
python main.py
```

The default endpoint is `http://localhost:8088/responses`.

## Demo Prompt

Use the included weak Azure export. The path is relative to the backend working directory used by the agent:

```text
samples/bad-config/azure-export.json を分析して、security / cost / architecture の固定JSONスキーマで結果を返してください。必要なら explore で先に棚卸ししてください。
```

## Deployment

Deploy the backend as a Foundry Hosted Agent with `azd ai agent init`, `azd provision`, and `azd deploy`. See [docs/deploy-hosted-agent.md](docs/deploy-hosted-agent.md).

After deployment, validate both input paths: the bundled fixture smoke test and the inline JSON request test. See [docs/hosted-agent-test-plan.md](docs/hosted-agent-test-plan.md) for the Hosted Agent verification checklist and concrete prompts.

## Status and Roadmap

| Area | Status |
| --- | --- |
| Part A inner harness | Implemented: MAF agent loop, specialist workflow, internal Skills, guarded tools. |
| Part A outer harness | Implemented: ResponsesHostServer, responses manifest, telemetry setup, workspace contract. |
| Part A next steps | Approval checkpoint, Invocations protocol, identity hardening. |
| Part B Observe | Implemented foundation: tracing helper, common attributes, startup/server observability context. |
| Part B Evaluate | Implemented foundation: ASSERT-like policy assets, local rubric scorecard, datasets, and optional Foundry cloud eval runner. |
| Part B next steps | Planned: request/run spans, trace evaluation, ACS policy/runtime, ROI metrics. |
| Frontend | Planned. |

## References

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Microsoft Agent Framework Documentation](https://learn.microsoft.com/agent-framework/)
- [Microsoft Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Microsoft Foundry Hosted Agents](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents?view=foundry)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## License

MIT License. See [LICENSE](LICENSE) for details.
