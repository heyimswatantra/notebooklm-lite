"""Parse citation labels from model answers (pure functions, no I/O)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Bracket contents must be comma-separated positive integers only (no ranges).
_LABEL_LIST_RE = re.compile(r"^\d+(?:\s*,\s*\d+)*$")
_BRACKET_RE = re.compile(r"\[([^\]]*)\]")


@dataclass(frozen=True)
class ParsedCitations:
    """Citation labels in first-appearance order (valid only), plus invalid."""

    cited_labels: list[int]
    invalid_labels: list[int]


def parse_citations(answer_text: str, valid_labels: set[int]) -> ParsedCitations:
    """Extract citation labels from *answer_text*.

    Supports ``[1]``, ``[1][3]``, and ``[1, 3]``. Ignores non-citation brackets
    such as ``[sic]`` or ``[1-3]``. Valid labels are deduplicated by first
    appearance; labels not in *valid_labels* are returned in *invalid_labels*
    (also deduplicated by first appearance).
    """
    cited_labels: list[int] = []
    cited_seen: set[int] = set()
    invalid_labels: list[int] = []
    invalid_seen: set[int] = set()

    for match in _BRACKET_RE.finditer(answer_text):
        content = match.group(1).strip()
        if not _LABEL_LIST_RE.fullmatch(content):
            continue
        for part in re.split(r"\s*,\s*", content):
            label = int(part)
            if label in cited_seen or label in invalid_seen:
                continue
            if label in valid_labels:
                cited_seen.add(label)
                cited_labels.append(label)
            else:
                invalid_seen.add(label)
                invalid_labels.append(label)

    return ParsedCitations(cited_labels=cited_labels, invalid_labels=invalid_labels)
