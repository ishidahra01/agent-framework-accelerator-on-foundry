---
name: azure-export-exploration
description: Azure export exploration guidance for resource inventories, inspected file paths, high-signal facts, and missing context. Use before security, cost, or architecture review when inputs contain Azure resources, ARM JSON, or multiple files.
---

Use this skill at the start of Azure infrastructure analysis.

Role in the single-agent review pipeline: exploration reviewer. Establish the evidence base before
security, cost, architecture, or synthesis work begins.

Inspect the provided request content, files, and Azure export structures. Return or retain a compact
inventory with:

1. Resource count by provider/type.
2. Files inspected and notable paths.
3. High-signal configuration facts for security, cost, and architecture review.
4. Missing context or files that would materially affect the analysis.

Stay factual. Do not perform the full security, cost, or architecture review unless the evidence is
so direct that it should be called out as an exploration note. Prefer concise summaries over copying
large JSON fragments.