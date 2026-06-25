"""Stable Azure analysis output contract.

This module is the single source of truth for the analysis output contract used by
the Azure Resource Analyzer agent. It is intentionally runtime-neutral: it has no
dependency on any specific agent SDK so it can be reused by prompt/instruction
generation, response validation, evaluation, governance, and demo comparison.

The contract is expressed as Pydantic models. ``response_format`` consumers (for
example Microsoft Agent Framework structured output) can pass
``AzureAnalysisResult`` directly, while validators can use
``EXPECTED_ANALYSIS_OUTPUT_SCHEMA`` (a plain JSON Schema dict).
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field


class AnalysisSummary(BaseModel):
    """Top-level counters that downstream evaluation and ROI logic depend on."""

    resourcesAnalyzed: int = Field(ge=0)
    securityFindings: int = Field(ge=0)
    costSavingsOpportunities: int = Field(ge=0)


class SecurityFinding(BaseModel):
    severity: str
    resource: str
    finding: str
    remediation: str


class CostRecommendation(BaseModel):
    resource: str
    recommendation: str
    estimatedSavings: str


class ArchitectureFinding(BaseModel):
    pillar: str
    finding: str
    recommendation: str


class AzureAnalysisResult(BaseModel):
    """The stable Azure analysis output contract.

    Keys are deliberately stable because evaluation, control, and ROI calculations
    depend on them. Categories without supported evidence should be empty arrays.
    """

    summary: AnalysisSummary
    security: list[SecurityFinding] = Field(default_factory=list)
    cost: list[CostRecommendation] = Field(default_factory=list)
    architecture: list[ArchitectureFinding] = Field(default_factory=list)


def expected_analysis_output_schema() -> dict[str, object]:
    """Return the JSON Schema for the analysis output contract."""

    return AzureAnalysisResult.model_json_schema()


# Backwards-compatible alias retained for validators and future ACS controls.
EXPECTED_ANALYSIS_OUTPUT_SCHEMA: dict[str, object] = expected_analysis_output_schema()


def analysis_output_instructions() -> str:
    """Prompt fragment that pins the stable Azure analysis output contract."""

    schema = json.dumps(EXPECTED_ANALYSIS_OUTPUT_SCHEMA, indent=2)
    return f"""
For Azure resource analysis tasks, synthesize the final answer around this stable contract:

```json
{{
  "summary": {{ "resourcesAnalyzed": 25, "securityFindings": 12, "costSavingsOpportunities": 8 }},
  "security": [{{ "severity": "Critical", "resource": "...", "finding": "...", "remediation": "..." }}],
  "cost": [{{ "resource": "...", "recommendation": "...", "estimatedSavings": "$15/month" }}],
  "architecture": [{{ "pillar": "Operational Excellence", "finding": "...", "recommendation": "..." }}]
}}
```

Use Japanese prose around the report when helpful, but keep these keys stable because evaluation,
control, and ROI calculations depend on them. If evidence is incomplete, return an empty array for
that category and explain the uncertainty outside the JSON contract.

Reference schema for validators and future ACS controls:

```json
{schema}
```
""".strip()
