"""Unit tests for rag/citations.parse_citations."""

from __future__ import annotations

import pytest

from backend.rag.citations import parse_citations


class TestParseCitations:
    def test_single_label(self) -> None:
        parsed = parse_citations("Answer [1].", {1, 2})
        assert parsed.cited_labels == [1]
        assert parsed.invalid_labels == []

    def test_adjacent_brackets(self) -> None:
        parsed = parse_citations("See [1][3].", {1, 2, 3})
        assert parsed.cited_labels == [1, 3]

    def test_comma_inside_brackets(self) -> None:
        parsed = parse_citations("See [1, 3].", {1, 2, 3})
        assert parsed.cited_labels == [1, 3]

    def test_first_appearance_order_and_deduplication(self) -> None:
        parsed = parse_citations("Refs [2][1][2] and [1, 2].", {1, 2})
        assert parsed.cited_labels == [2, 1]

    def test_invalid_label(self) -> None:
        parsed = parse_citations("Bad [9] ref.", {1, 2})
        assert parsed.cited_labels == []
        assert parsed.invalid_labels == [9]

    def test_mixed_valid_and_invalid(self) -> None:
        parsed = parse_citations("Mix [1][9].", {1, 2})
        assert parsed.cited_labels == [1]
        assert parsed.invalid_labels == [9]

    def test_sic_ignored(self) -> None:
        parsed = parse_citations("Quote [sic] with [1].", {1})
        assert parsed.cited_labels == [1]
        assert parsed.invalid_labels == []

    def test_range_unsupported(self) -> None:
        parsed = parse_citations("Range [1-3] and [1].", {1, 2, 3})
        assert parsed.cited_labels == [1]
        assert parsed.invalid_labels == []

    def test_no_brackets(self) -> None:
        parsed = parse_citations("Plain answer.", {1})
        assert parsed.cited_labels == []
        assert parsed.invalid_labels == []

    def test_invalid_deduplicated(self) -> None:
        parsed = parse_citations("[9][9]", {1})
        assert parsed.invalid_labels == [9]
