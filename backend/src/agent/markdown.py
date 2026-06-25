"""Small helper to parse YAML frontmatter from markdown documents."""

from __future__ import annotations

from typing import Any

import yaml

_DELIMITER = "---"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split ``text`` into (frontmatter mapping, body).

    Returns an empty mapping and the original text when no frontmatter block is
    present. Raises ``ValueError`` when a frontmatter block is opened but not
    terminated or is not a YAML mapping.
    """

    stripped = text.lstrip("\ufeff")
    if not stripped.startswith(_DELIMITER):
        return {}, text.strip()

    after_open = stripped[len(_DELIMITER):].lstrip("\r\n")
    end = after_open.find(f"\n{_DELIMITER}")
    if end == -1:
        raise ValueError("Frontmatter block is not terminated.")

    frontmatter_text = after_open[:end]
    body = after_open[end + len(_DELIMITER) + 1:]

    metadata = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(metadata, dict):
        raise ValueError("Frontmatter must be a YAML mapping.")

    return metadata, body.strip()
