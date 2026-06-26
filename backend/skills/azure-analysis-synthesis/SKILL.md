---
name: azure-analysis-synthesis
description: Azure analysis synthesis guidance for merging exploration, security, cost, and architecture findings into the stable JSON contract. Use after role-specific review evidence has been gathered.
---

Use this skill at the end of Azure infrastructure analysis.

Role in the single-agent review pipeline: final synthesizer. Merge the exploration, security, cost,
and architecture evidence into one coherent answer without inventing unsupported findings.

When producing the final analysis:

1. Preserve the required top-level JSON keys: `summary`, `security`, `cost`, and `architecture`.
2. Use empty arrays when no finding is supported by evidence.
3. Tie every finding to a concrete resource name, type, or exported configuration fact.
4. Keep confirmed findings separate from assumptions or validation needs.
5. Do not duplicate the same issue across dimensions unless it has distinct security, cost, or
   reliability consequences.
6. Respond in Japanese unless the user explicitly asks for another language.

For narrative responses, keep the same review order: executive summary, security, cost,
architecture/reliability, and recommended actions.