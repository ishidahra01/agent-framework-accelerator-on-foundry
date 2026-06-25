# Security model

The agent treats all tool use as potentially risky. Guardrails are centralized in `backend/src/agent/tools/guardrails.py` and applied by every tool factory in `backend/src/agent/tools/`.

## Filesystem access

- **Scoped to approved roots.** `resolve_within_root()` resolves every path against the project root or the workspace root and rejects anything that escapes it, blocking path traversal (`../`, absolute paths outside the root).
- **Secret denylist.** `is_denied_path()` denies any path whose basename is `.env`, starts with `.env.`, or whose path contains a `secrets` segment. Both read (`ensure_readable`) and write (`ensure_writable`) paths enforce this.
- Secrets are never written into workspaces, logs, generated reports, or test fixtures.

## Shell execution

The shell tool is **disabled by default** and only built when `AGENT_ENABLE_SHELL_TOOL=true`.

When enabled, `ensure_command_allowed()` rejects:

- recursive force deletes (`rm -rf`, `rm -fr`)
- `git push`
- pipe-to-shell installers (`curl|sh`, `wget|bash`, `iwr|pwsh`, etc.)
- filesystem destroyers (`mkfs`, `dd if=`, writes to `/dev/sd*`)
- `Remove-Item -Recurse -Force`, `del /s`, `del /q`
- power-state commands (`shutdown`, `reboot`, `halt`, `poweroff`)
- fork bombs

Shell execution also applies a timeout (`DEFAULT_SHELL_TIMEOUT_SECONDS = 30`) and truncates output to `DEFAULT_MAX_OUTPUT_BYTES = 64 KiB` via `truncate_output()`.

## Tool surface design

Tool roots (project root, workspace root) are bound through factory closures (`build_default_tools(project_root, workspace_root, enable_shell)`), so they never appear in the model-visible tool signatures. The model only sees the logical parameters (e.g. a path relative to the workspace).

## Authentication

The runtime authenticates to Foundry with `DefaultAzureCredential` (`azure-identity`). Locally this resolves to `az login`; in Hosted Agent deployments it resolves to managed identity. No API keys are stored or required.

## Validation

Guardrail behaviour is covered by `tests/test_tool_guardrails.py`. Run:

```powershell
python -m pytest tests/test_tool_guardrails.py
```

## Planned controls (Part B)

- Hosted Agent content safety / Azure Content Safety policy integration.
- An approval checkpoint before high-impact actions.
- Deterministic input/LLM/state/tool/output controls via an ACS policy layer.
