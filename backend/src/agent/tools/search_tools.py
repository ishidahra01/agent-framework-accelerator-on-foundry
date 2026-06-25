"""Search tools (glob + grep) constrained by guardrails.

These replace the Claude built-in ``Glob``/``Grep`` capabilities with explicit,
root-constrained functions.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from .guardrails import GuardrailError, is_denied_path, resolve_within_root

LOGGER = logging.getLogger("azure_resource_analyzer.tools.search")

MAX_RESULTS = 200


def build_search_tools(*, read_roots: Sequence[Path]) -> list[Callable[..., str]]:
    """Build glob/grep tools bound to the given read roots."""

    resolved_roots = [Path(root).resolve() for root in read_roots]

    def glob_files(pattern: str) -> str:
        """Find files matching a glob pattern under the project/workspace roots.

        Args:
            pattern: A glob pattern such as ``**/*.json`` or ``samples/*.json``.
        """

        matches: list[str] = []
        for root in resolved_roots:
            for match in root.glob(pattern):
                if match.is_file() and not is_denied_path(match):
                    matches.append(str(match))
                if len(matches) >= MAX_RESULTS:
                    break
        LOGGER.info("glob_files %r -> %d match(es)", pattern, len(matches))
        return "\n".join(sorted(set(matches))) or "(no matches)"

    def grep_files(query: str, glob: str = "**/*") -> str:
        """Search file contents for a regex within files matching a glob.

        Args:
            query: A regular expression to search for.
            glob: Glob limiting which files are scanned (default all files).
        """

        try:
            regex = re.compile(query)
        except re.error as exc:
            raise GuardrailError(f"Invalid regex {query!r}: {exc}") from exc

        results: list[str] = []
        for root in resolved_roots:
            for path in root.glob(glob):
                if not path.is_file() or is_denied_path(path):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for lineno, line in enumerate(text.splitlines(), start=1):
                    if regex.search(line):
                        results.append(f"{path}:{lineno}: {line.strip()}")
                        if len(results) >= MAX_RESULTS:
                            break
                if len(results) >= MAX_RESULTS:
                    break
        LOGGER.info("grep_files %r -> %d hit(s)", query, len(results))
        return "\n".join(results) or "(no matches)"

    return [glob_files, grep_files]
