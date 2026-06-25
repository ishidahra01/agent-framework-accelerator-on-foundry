"""Azure export inspection tools.

Deterministic helpers for parsing ARM-style Azure resource exports. The export
shape is a JSON object with a top-level ``resources`` array of objects that each
carry ``type``, ``name``, ``location``, and ``properties`` keys (see
``backend/samples/bad-config/azure-export.json``).
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .guardrails import GuardrailError, ensure_readable

LOGGER = logging.getLogger("azure_resource_analyzer.tools.azure_export")


def _load_export(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GuardrailError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GuardrailError(f"{path} is not an object export.")
    return data


def summarize_export(data: dict[str, Any]) -> dict[str, Any]:
    """Return a compact inventory of an Azure export object."""

    resources = data.get("resources", [])
    if not isinstance(resources, list):
        resources = []

    type_counts: Counter[str] = Counter()
    names: list[str] = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        type_counts[str(resource.get("type", "Unknown"))] += 1
        name = resource.get("name")
        if name:
            names.append(str(name))

    return {
        "resourceCount": len(names),
        "resourceTypeCounts": dict(sorted(type_counts.items())),
        "resourceNames": names,
        "metadata": data.get("metadata", {}),
    }


def build_azure_export_tools(*, read_roots: Sequence[Path]) -> list[Callable[..., str]]:
    """Build the Azure export inspection tool bound to the read roots."""

    resolved_roots = [Path(root).resolve() for root in read_roots]

    def _resolve(path: str) -> Path:
        last_error: GuardrailError | None = None
        for root in resolved_roots:
            try:
                return ensure_readable(root, path)
            except GuardrailError as exc:
                last_error = exc
        raise last_error or GuardrailError(f"No readable root for {path!r}.")

    def inspect_azure_export(path: str) -> str:
        """Summarize an Azure resource export: counts by type and resource names.

        Args:
            path: Path to a JSON Azure export, relative to the project/workspace.
        """

        target = _resolve(path)
        LOGGER.info("inspect_azure_export %s", target)
        summary = summarize_export(_load_export(target))
        return json.dumps(summary, indent=2, ensure_ascii=False)

    return [inspect_azure_export]
