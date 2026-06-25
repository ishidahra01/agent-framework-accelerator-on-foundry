# Copilot repository instructions

## Repository purpose

This repository is a Microsoft-native accelerator for building, running, and deploying enterprise AI agents with:

* Microsoft Foundry
* Microsoft Agent Framework
* GitHub Copilot SDK integration for Microsoft Agent Framework, where appropriate
* Foundry Hosted Agents as the target deployment environment

The repository should prioritize clear architecture, practical samples, secure defaults, and documentation that helps developers understand how to build production-oriented agents.

## Source of truth

When implementing or changing runtime behavior, always use the latest official documentation and SDK/API specifications as the source of truth.

Prioritize these sources:

* Microsoft Learn documentation for Microsoft Agent Framework
* Microsoft Learn documentation for Microsoft Foundry and Foundry Hosted Agents
* GitHub Docs for GitHub Copilot SDK
* GitHub Docs for GitHub Copilot SDK integration with Microsoft Agent Framework
* Official package documentation and source examples for the SDK versions used in this repository

Do not rely only on memory for API names, SDK behavior, environment variables, deployment manifests, or preview feature behavior.

When using a newly introduced or preview API, add a short comment or documentation note explaining:

* which official API or SDK version it depends on
* whether the behavior is stable, preview, or subject to change
* how developers can validate or update it later

## Architecture principles

Use Microsoft Agent Framework as the primary application framework for agent runtime design.

Prefer:

* explicit agent construction
* clear tool registration
* typed inputs and outputs where practical
* workflow-based orchestration for multi-step or multi-agent processes
* simple functions for deterministic steps that do not need an LLM
* well-defined interfaces between runtime, tools, skills, workspace, and deployment code

Use agents when the task is open-ended, conversational, or requires autonomous tool use.

Use workflows when the task has explicit stages, ordered execution, branching, checkpointing, or multiple specialists that need to coordinate.

Use normal Python functions or services when deterministic code is sufficient.

## GitHub Copilot SDK integration

GitHub Copilot SDK may be used when it provides meaningful value for repo-aware, coding-oriented, shell/file, or developer-agent scenarios.

When integrated with Microsoft Agent Framework, keep the integration behind a clear adapter or provider boundary.

Do not tightly couple the entire application runtime to GitHub Copilot SDK unless that is the explicit design goal.

Prefer a structure where Microsoft Agent Framework owns orchestration and the Copilot SDK provider is one possible agent or execution backend.

## Internal skills

This repository may define internal Skills or playbooks used by the target agent application.

These internal Skills are application runtime assets, not GitHub Copilot repository customization files.

Prefer locations such as:

```text
backend/skills/
backend/src/agent/skills/
```

Do not place application runtime Skills under `.github/skills` unless the intent is specifically to customize GitHub Copilot itself.

Skill implementations should be:

* discoverable
* documented
* versionable
* easy to test
* loaded explicitly by the runtime or workflow
* separate from repository-level Copilot instructions

## Repository structure

Keep the repository easy to navigate.

Prefer a structure similar to:

```text
backend/
  main.py
  agent.yaml
  Dockerfile
  src/
    agent/
      runtime.py
      workflow.py
      workspace.py
      contracts/
      skills/
      tools/
      telemetry/
  skills/
  samples/

docs/
  architecture.md
  deployment.md
  local-development.md
  skills.md
  security-model.md
  evaluation.md

tests/
  unit/
  integration/

.github/
  copilot-instructions.md
  workflows/
```

Avoid mixing unrelated concerns in a single file.

Keep these boundaries clear:

* runtime construction
* workflow orchestration
* tool implementations
* skill loading
* model/provider configuration
* workspace and artifact handling
* deployment manifests
* tests
* documentation

## Documentation expectations

When adding or changing functionality, update documentation in the same change when practical.

Documentation should explain:

* what the feature does
* why the design was chosen
* how to run it locally
* how to deploy it
* how to validate it
* known limitations
* security or operational considerations

Prefer short, practical docs over long conceptual docs unless architecture clarity requires more detail.

Use diagrams or text-based architecture blocks when they make the flow easier to understand.

## Code quality

Prefer simple, readable, maintainable code.

Follow these principles:

* keep functions small and focused
* use explicit names
* avoid hidden global state
* avoid large untyped dictionaries for core runtime contracts
* use dataclasses or Pydantic models for structured data where useful
* centralize configuration loading
* validate required environment variables at startup
* fail fast with actionable error messages
* avoid broad exception swallowing
* keep provider-specific code isolated

Do not introduce unnecessary frameworks or dependencies.

If a dependency is added, document why it is needed.

## Configuration

Use environment variables for deployment-specific configuration.

Keep local examples in `.env.example`, but never commit real secrets.

Do not read or write secrets into workspaces, logs, generated reports, or test fixtures.

Prefer clear environment variable names that describe the application concept, for example:

```text
FOUNDRY_PROJECT_ENDPOINT
FOUNDRY_MODEL_DEPLOYMENT
FOUNDRY_AGENT_NAME
FOUNDRY_AGENT_VERSION
AGENT_WORKSPACE_ROOT
APPLICATIONINSIGHTS_CONNECTION_STRING
AZURE_MONITOR_CONNECTION_STRING
PORT
```

## Security and safety

Treat all agent tool use as potentially risky.

When implementing tools that access files, shell commands, network resources, or external systems:

* restrict scope by default
* validate inputs
* deny access to secrets and `.env` files
* constrain filesystem access to approved directories
* apply command allowlists or denylists for shell execution
* add timeouts
* limit output size
* log tool calls safely
* avoid logging sensitive data
* require explicit design justification for destructive operations

The agent should be useful, but not overly permissive.

## Testing and validation

Add tests for new runtime, workflow, skill, tool, and contract behavior.

Prefer tests that cover:

* agent/workflow construction
* skill loading
* output contract generation
* workspace path resolution
* configuration validation
* tool guardrails
* sample input processing
* import and startup validation

When changing Python code, run:

```bash
python -m compileall backend
python -m pytest
```

If tests are not yet available, add the smallest useful test coverage rather than leaving behavior unvalidated.

## Pull request expectations

Keep pull requests focused and reviewable.

Each PR should include:

* a clear summary
* implementation notes
* validation commands run
* known limitations
* documentation updates if needed

For larger changes, propose a plan before making broad edits.

Do not combine unrelated refactoring, dependency changes, runtime changes, and documentation rewrites in one PR unless explicitly requested.

## Style

Use English for code, comments, filenames, doc headings, and developer-facing repository documentation unless there is a specific reason to use Japanese.

User-facing demo responses may default to Japanese when the sample scenario requires it.

Prefer concise comments that explain why the code exists, not comments that merely repeat what the code does.
