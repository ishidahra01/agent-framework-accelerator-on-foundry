# Microsoft Foundry Agent Development Accelerator

This repository is hands-on content for learning how to build, host, observe, evaluate, and improve enterprise agents with **Microsoft Foundry** and the **Microsoft Agent Framework (MAF)**.

The concrete sample is an Azure Well-Architected review agent, but the main purpose is broader than Azure resource analysis. The sample gives the repo a realistic workload for deep dives into agent harness design, Hosted Agent deployment, observability, evaluation, and optimization.

> **Migrating from the Claude Agent SDK build?** Earlier revisions used the Claude Agent SDK as the inner harness. The runtime is now MAF-native and Claude-free. See [docs/migration-from-claude-agent-sdk.md](docs/migration-from-claude-agent-sdk.md) for the mapping between the old and new components.

> Some deep dive documents still preserve historical notes from the pre-MAF migration. Use [docs/architecture.md](docs/architecture.md) as the source of truth for the current MAF runtime, and use the deep dives for the product concepts and implementation path.

## What You Can Learn Here

| Deep dive | What this repo demonstrates | Start here |
| --- | --- | --- |
| Agent development on MAF | Explicit agent construction, `FoundryChatClient`, tools, internal Skills, structured output, and workflow orchestration. | [docs/architecture.md](docs/architecture.md) |
| Harness design | How the agent loop, tools, state, output contracts, hosting boundary, and telemetry fit together. | [docs/architecture.md](docs/architecture.md), [docs/harness-deepdive.md](docs/harness-deepdive.md) |
| Foundry Hosted Agent deployment | Packaging the backend as a Hosted Agent with a responses endpoint, sandboxed filesystem, environment contract, and deployment validation. | [docs/deploy-hosted-agent.md](docs/deploy-hosted-agent.md), [docs/hosted-agent-test-plan.md](docs/hosted-agent-test-plan.md) |
| Observability and evaluation | OpenTelemetry context, App Insights / Foundry trace readiness, local policy checks, rubric scorecards, and Foundry evaluation handoff. | [docs/trust-roi-deepdive.md](docs/trust-roi-deepdive.md), [docs/foundry-portal-rubric-evaluation.md](docs/foundry-portal-rubric-evaluation.md) |
| Optimization loop | Agent Optimizer baseline / candidate configuration and evaluation-driven improvement. | [docs/foundry-agent-optimizer.md](docs/foundry-agent-optimizer.md), [docs/foundry-agent-optimizer-concepts.md](docs/foundry-agent-optimizer-concepts.md) |

## Why Foundry?

Foundry is the outer managed runtime for this accelerator. It matters because a useful enterprise agent is not just a local prompt loop; it needs a production surface around it.

| Need | Foundry / Hosted Agent role in this repo |
| --- | --- |
| Hosted endpoint | Exposes the MAF backend through the Hosted Agent responses protocol. |
| Managed execution boundary | Runs the custom backend in a hosted container with a clear deployment and environment contract. |
| Workspace and state boundary | Provides a session-oriented filesystem surface so generated files and intermediate artifacts have a predictable home. |
| Identity and secure configuration | Uses `DefaultAzureCredential` locally or managed identity when deployed; no API keys are required for the main MAF runtime path. |
| Observability | Bridges runtime telemetry into Foundry / Application Insights so agent runs can be traced, debugged, and evaluated. |
| Evaluation and optimization | Connects the deployed agent to rubric evaluation, cloud evaluation automation, and Agent Optimizer workflows. |

Details live in [docs/deploy-hosted-agent.md](docs/deploy-hosted-agent.md), [docs/hosted-agent-test-plan.md](docs/hosted-agent-test-plan.md), and [docs/trust-roi-deepdive.md](docs/trust-roi-deepdive.md).

## Why Microsoft Agent Framework?

MAF is the inner harness for this accelerator: the code-level runtime that decides how the agent is built, how it calls the model, how tools are registered, how specialists coordinate, and how output is shaped.

In this repo, a harness means the runtime scaffolding around the model. It includes instructions, model client selection, tools, Skills, workflow routing, workspace handling, guardrails, output contracts, and telemetry hooks. Agents need that harness because reliable behavior comes from repeatable runtime structure, not from a prompt alone.

MAF is used here because it provides:

- explicit `Agent` construction instead of hidden runtime state
- `FoundryChatClient` integration for Foundry model deployments
- workflow-based specialist orchestration for explore, security, cost, architecture, and synthesis steps
- tool registration through normal Python functions with local guardrails
- structured output contracts that evaluation and control code can validate
- observability integration points for model, tool, and application traces

The current implementation can run in `workflow` mode, where specialists are wired through a MAF workflow, or `single` mode, where one coordinator agent receives all tools and Skills. See [docs/architecture.md](docs/architecture.md) for the current runtime walkthrough.

## What Is Implemented

- MAF-native runtime construction with `Agent` + `FoundryChatClient`
- Multi-specialist workflow: explore -> security / cost / architecture -> synthesize
- Internal Skills under `backend/skills/` for Azure WAF, security, and cost review guidance
- Guarded file, search, Azure export, and optional shell tools
- Stable pydantic output contract for analysis results
- Hosted Agent responses server entrypoint in `backend/main.py`
- Hosted Agent manifest in `backend/agent.yaml`
- Observability foundation with OpenTelemetry attributes and App Insights / Azure Monitor environment normalization
- Local evaluation assets: policy YAML, rubric YAML, JSONL datasets, and scorecard helper
- Optional Foundry cloud evaluation runner and Agent Optimizer configuration bridge

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
  -> observability and evaluation assets
```

The architecture is described in [docs/architecture.md](docs/architecture.md). Skills are documented in [docs/skills.md](docs/skills.md), and tool guardrails are documented in [docs/security-model.md](docs/security-model.md).

## Sample Scenario

The sample agent reviews Azure exports, ARM-style JSON, or resource configuration snapshots. It returns security findings, cost recommendations, and architecture guidance through this stable contract:

```json
{
  "summary": { "resourcesAnalyzed": 25, "securityFindings": 12, "costSavingsOpportunities": 8 },
  "security": [ { "severity": "Critical", "resource": "...", "finding": "...", "remediation": "..." } ],
  "cost": [ { "resource": "...", "recommendation": "...", "estimatedSavings": "$15/month" } ],
  "architecture": [ { "pillar": "Operational Excellence", "finding": "...", "recommendation": "..." } ]
}
```

The contract is centralized in `backend/src/agent/contracts/azure_analysis.py` and appended to the runtime prompt in `backend/src/agent/runtime.py`. Part B uses the same shape for policy checks, rubric scoring, future controls, optimization, and ROI.

## Repository Layout

```text
backend/
  main.py                         # Hosted Agent entrypoint (ResponsesHostServer)
  agent.yaml                      # azd / Hosted Agent manifest
  agents/                         # coordinator and specialist instructions
  skills/                         # internal Azure WAF, security, and cost Skills
  optimizer_configs/              # Agent Optimizer baseline overlay
  src/agent/
    runtime.py                    # Agent + FoundryChatClient construction
    workflow.py                   # specialist workflow construction
    instructions.py               # loads agents/*.md and composes system instructions
    workspace.py                  # Hosted workspace root helper
    contracts/azure_analysis.py   # stable output schema and prompt contract
    skills/                       # Skills loader / registry
    tools/                        # guarded tools
    optimization.py               # Agent Optimizer runtime config bridge
    observability/tracing.py      # Observe helper and trace attribute contract
    observability/evaluation.py   # local policy / rubric scorecard helper
  samples/
    bad-config/azure-export.json  # deliberately weak demo input
evals/                            # policy, rubric, conversation, and JSONL evaluation assets
scripts/
  run_foundry_agent_eval.py       # optional Foundry cloud evaluation runner
docs/                             # architecture, deployment, harness, observability, evaluation, optimizer guides
tests/                            # unit and construction tests
```

## Local Development

From the repository root:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configure Foundry access through `backend/.env` or environment variables. See `backend/.env.example` for the full list.

```env
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<deployment-name>
AGENT_RUNTIME_MODE=workflow
AGENT_WORKSPACE_ROOT=work
```

Authentication uses `DefaultAzureCredential`: run `az login` locally, or rely on managed identity when deployed.

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

## Testing and Validation

Install the test dependencies and run the suite from the repository root:

```powershell
pip install -r backend/requirements-dev.txt
python -m compileall -q backend scripts tests
python -m pytest tests/ -q
```

The pure-Python tests run without Microsoft Agent Framework installed. When MAF is installed, `tests/test_maf_construction.py` also exercises real `Agent` / `Workflow` construction with an injected fake chat client, so no Foundry endpoint is required to verify the wiring.

## Status and Roadmap

| Area | Status |
| --- | --- |
| Part A harness | Implemented: MAF agent loop, specialist workflow, internal Skills, guarded tools, Hosted Agent responses entrypoint. |
| Part B Observe | Implemented foundation: trace helper, common attributes, startup/server observability context. |
| Part B Evaluate | Implemented foundation: policy assets, local rubric scorecard, seed datasets, optional Foundry cloud eval runner. |
| Part B Optimize | Implemented foundation: Agent Optimizer baseline/candidate config bridge. |
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
