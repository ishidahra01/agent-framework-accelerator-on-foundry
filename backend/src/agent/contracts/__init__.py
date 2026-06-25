"""Runtime-neutral contracts for the Azure Resource Analyzer agent."""

from __future__ import annotations

from .azure_analysis import (
    EXPECTED_ANALYSIS_OUTPUT_SCHEMA,
    AnalysisSummary,
    ArchitectureFinding,
    AzureAnalysisResult,
    CostRecommendation,
    SecurityFinding,
    analysis_output_instructions,
    expected_analysis_output_schema,
)

__all__ = [
    "EXPECTED_ANALYSIS_OUTPUT_SCHEMA",
    "AnalysisSummary",
    "ArchitectureFinding",
    "AzureAnalysisResult",
    "CostRecommendation",
    "SecurityFinding",
    "analysis_output_instructions",
    "expected_analysis_output_schema",
]
