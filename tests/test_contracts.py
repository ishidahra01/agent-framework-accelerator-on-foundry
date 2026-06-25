"""Tests for the stable Azure analysis output contract (PR1)."""

from __future__ import annotations

import json

import pytest

from src.agent.contracts import (
    EXPECTED_ANALYSIS_OUTPUT_SCHEMA,
    AzureAnalysisResult,
    analysis_output_instructions,
)
from src.agent import runtime_contracts


VALID_PAYLOAD = {
    "summary": {
        "resourcesAnalyzed": 25,
        "securityFindings": 12,
        "costSavingsOpportunities": 8,
    },
    "security": [
        {
            "severity": "Critical",
            "resource": "stg-public",
            "finding": "Blob container is publicly accessible.",
            "remediation": "Disable anonymous access.",
        }
    ],
    "cost": [
        {
            "resource": "vm-oversized",
            "recommendation": "Resize to a smaller SKU.",
            "estimatedSavings": "$15/month",
        }
    ],
    "architecture": [
        {
            "pillar": "Operational Excellence",
            "finding": "No diagnostics configured.",
            "recommendation": "Enable diagnostic settings.",
        }
    ],
}


def test_valid_payload_parses() -> None:
    result = AzureAnalysisResult.model_validate(VALID_PAYLOAD)
    assert result.summary.resourcesAnalyzed == 25
    assert result.security[0].severity == "Critical"
    assert result.cost[0].estimatedSavings == "$15/month"
    assert result.architecture[0].pillar == "Operational Excellence"


def test_empty_categories_allowed() -> None:
    payload = {
        "summary": {
            "resourcesAnalyzed": 0,
            "securityFindings": 0,
            "costSavingsOpportunities": 0,
        }
    }
    result = AzureAnalysisResult.model_validate(payload)
    assert result.security == []
    assert result.cost == []
    assert result.architecture == []


def test_negative_counts_rejected() -> None:
    payload = {
        "summary": {
            "resourcesAnalyzed": -1,
            "securityFindings": 0,
            "costSavingsOpportunities": 0,
        }
    }
    with pytest.raises(ValueError):
        AzureAnalysisResult.model_validate(payload)


def test_missing_summary_rejected() -> None:
    with pytest.raises(ValueError):
        AzureAnalysisResult.model_validate({"security": []})


def test_schema_top_level_keys() -> None:
    schema = EXPECTED_ANALYSIS_OUTPUT_SCHEMA
    properties = schema["properties"]
    for key in ("summary", "security", "cost", "architecture"):
        assert key in properties


def test_instructions_contain_contract_keys() -> None:
    text = analysis_output_instructions()
    for key in ("summary", "security", "cost", "architecture"):
        assert key in text
    # The embedded reference schema must be valid JSON.
    start = text.rindex("```json") + len("```json")
    end = text.rindex("```")
    json.loads(text[start:end].strip())


def test_runtime_contracts_shim_reexports() -> None:
    assert runtime_contracts.analysis_output_instructions() == analysis_output_instructions()
    assert runtime_contracts.EXPECTED_ANALYSIS_OUTPUT_SCHEMA == EXPECTED_ANALYSIS_OUTPUT_SCHEMA
