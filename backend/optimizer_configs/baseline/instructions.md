# Azure Resource Analyzer Optimizer Overlay

This file is the Agent Optimizer baseline overlay. Keep the long-lived agent instructions in `backend/agents/` and the internal Skills in `backend/skills/`.

Optimization goals:

1. Improve how the coordinator plans Azure resource reviews.
2. Improve evidence-grounded synthesis across security, cost, and architecture findings.
3. Reduce vague recommendations that do not name an affected resource or configuration.
4. Preserve Japanese responses unless the user requests another language.
5. Preserve delegation to the explore, security, cost, and architecture specialists when useful.

The application appends the stable output schema, workspace boundary, and hosted runtime constraints at startup. Do not duplicate those long-lived constraints here.