"""Tests for rag/chunking.py.

Tests build PageText objects directly (no PDF needed) and verify
chunk counts, boundaries, overlap, and edge cases.
"""
from __future__ import annotations

import tiktoken
import pytest

from backend.rag.chunking import Chunk, chunk_pages
from backend.rag.extraction import PageText


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Same encoding used by chunking.py
_ENC = tiktoken.get_encoding("cl100k_base")


def _make_text_with_n_tokens(n: int) -> str:
    """Return a string that encodes to exactly ``n`` tokens.

    Generates a long numbered-word string, takes the first ``n`` tokens,
    decodes back to text, and verifies the round-trip.
    """
    # "word0 word1 word2 ..." — each "wordN" is usually 1-2 tokens,
    # and spaces merge with the next word.  We generate far more than
    # needed and truncate to exactly n tokens.
    source = " ".join(f"word{i}" for i in range(n * 3))
    tokens = _ENC.encode(source, disallowed_special=())
    text = _ENC.decode(tokens[:n])

    # Verify the round-trip gives exactly n tokens.
    actual = len(_ENC.encode(text, disallowed_special=()))
    assert actual == n, f"Expected {n} tokens, got {actual}"
    return text


def _page(page_number: int, text: str) -> PageText:
    """Shorthand for creating a PageText."""
    return PageText(page_number=page_number, text=text)


# ---------------------------------------------------------------------------
# Basic behavior
# ---------------------------------------------------------------------------

class TestChunkBasics:

    def test_short_page_single_chunk(self) -> None:
        """A page shorter than max_tokens gives exactly one chunk."""
        text = _make_text_with_n_tokens(100)
        pages = [_page(1, text)]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].page_number == 1
        assert chunks[0].token_count == 100

    def test_long_page_multiple_chunks(self) -> None:
        """A page longer than max_tokens is split into multiple chunks."""
        text = _make_text_with_n_tokens(1200)
        pages = [_page(1, text)]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        assert len(chunks) > 1
        # First chunk should be max_tokens
        assert chunks[0].token_count == 500

    def test_overlap_content(self) -> None:
        """End of chunk N overlaps with start of chunk N+1."""
        text = _make_text_with_n_tokens(600)
        pages = [_page(1, text)]
        # max_tokens=500, overlap=50, stride=450
        # Chunk 0: tokens[0:500], Chunk 1: tokens[450:600]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        assert len(chunks) == 2
        # The overlap region (tokens 450-500) should appear in both chunks.
        # Verify by checking that the end of chunk 0 appears at the start
        # of chunk 1.
        tail_of_first = chunks[0].text[-50:]  # approximate overlap text
        assert tail_of_first in chunks[1].text or chunks[1].text.startswith(tail_of_first[:20])

    def test_chunk_index_sequential(self) -> None:
        """chunk_index is 0, 1, 2, … across all pages."""
        pages = [
            _page(1, _make_text_with_n_tokens(600)),
            _page(2, _make_text_with_n_tokens(100)),
        ]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunks_never_cross_pages(self) -> None:
        """Each chunk's page_number matches its source page."""
        pages = [
            _page(1, _make_text_with_n_tokens(600)),
            _page(3, _make_text_with_n_tokens(200)),  # page 3 (skipped page 2)
        ]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        # Page 1 produces 2 chunks; page 3 produces 1 chunk.
        page_numbers = [c.page_number for c in chunks]
        assert page_numbers == [1, 1, 3]

    def test_custom_parameters(self) -> None:
        """Passing different max_tokens/overlap_tokens works."""
        text = _make_text_with_n_tokens(200)
        pages = [_page(1, text)]
        chunks = chunk_pages(pages, max_tokens=100, overlap_tokens=20)

        # 200 tokens, max=100, stride=80
        # Chunk 0: [0:100], Chunk 1: [80:180], Chunk 2: [160:200]
        assert len(chunks) == 3
        assert chunks[0].token_count == 100
        assert chunks[1].token_count == 100
        assert chunks[2].token_count == 40  # 200 - 160


# ---------------------------------------------------------------------------
# Edge cases: empty / blank pages
# ---------------------------------------------------------------------------

class TestChunkEmptyPages:

    def test_empty_pages_produce_no_chunks(self) -> None:
        """Empty-text pages produce no chunks."""
        pages = [_page(1, ""), _page(2, "   \n\t  ")]
        chunks = chunk_pages(pages)
        assert chunks == []

    def test_mixed_empty_and_text_pages(self) -> None:
        """Only pages with real text produce chunks."""
        pages = [
            _page(1, ""),
            _page(2, "Hello world"),
            _page(3, "   "),
        ]
        chunks = chunk_pages(pages)
        assert len(chunks) == 1
        assert chunks[0].page_number == 2


# ---------------------------------------------------------------------------
# Exact boundary tests (page token lengths 500, 501, 950, 951, 1000)
# ---------------------------------------------------------------------------

class TestExactBoundaries:
    """Verify chunk counts and token boundaries for specific page sizes.

    With max_tokens=500 and overlap_tokens=50 (stride=450):
    - 500 tokens  → 1 chunk:  [0:500]
    - 501 tokens  → 2 chunks: [0:500], [450:501]
    - 950 tokens  → 2 chunks: [0:500], [450:950]
    - 951 tokens  → 3 chunks: [0:500], [450:950], [900:951]
    - 1000 tokens → 3 chunks: [0:500], [450:950], [900:1000]
    """

    @pytest.fixture(params=[
        # (page_tokens, expected_chunk_count, expected_token_counts)
        (500,  1, [500]),
        (501,  2, [500, 51]),
        (950,  2, [500, 500]),
        (951,  3, [500, 500, 51]),
        (1000, 3, [500, 500, 100]),
    ])
    def boundary_case(self, request: pytest.FixtureRequest):
        """Parametrized fixture for boundary cases."""
        return request.param

    def test_chunk_count(self, boundary_case) -> None:
        n, expected_count, _ = boundary_case
        text = _make_text_with_n_tokens(n)
        chunks = chunk_pages([_page(1, text)], max_tokens=500, overlap_tokens=50)
        assert len(chunks) == expected_count, (
            f"For {n} tokens expected {expected_count} chunks, got {len(chunks)}"
        )

    def test_token_counts(self, boundary_case) -> None:
        n, _, expected_token_counts = boundary_case
        text = _make_text_with_n_tokens(n)
        chunks = chunk_pages([_page(1, text)], max_tokens=500, overlap_tokens=50)
        actual = [c.token_count for c in chunks]
        assert actual == expected_token_counts, (
            f"For {n} tokens expected token_counts={expected_token_counts}, "
            f"got {actual}"
        )


# ---------------------------------------------------------------------------
# No tiny trailing chunk
# ---------------------------------------------------------------------------

class TestNoTinyTrailingChunk:

    def test_no_trailing_chunk_at_exact_boundary(self) -> None:
        """When the last window reaches exactly the end, no extra chunk."""
        # 950 tokens with stride 450: window 0=[0:500], window 1=[450:950]
        # Window 1 reaches the end → stop.  No third chunk.
        text = _make_text_with_n_tokens(950)
        chunks = chunk_pages([_page(1, text)], max_tokens=500, overlap_tokens=50)
        assert len(chunks) == 2

    def test_just_past_boundary_gets_small_chunk(self) -> None:
        """951 tokens → 3 chunks.  The last chunk is small but necessary
        because the previous window did NOT reach the end."""
        text = _make_text_with_n_tokens(951)
        chunks = chunk_pages([_page(1, text)], max_tokens=500, overlap_tokens=50)
        assert len(chunks) == 3
        # Last chunk: tokens[900:951] → 51 tokens
        assert chunks[2].token_count == 51


# ---------------------------------------------------------------------------
# Special-token strings
# ---------------------------------------------------------------------------

class TestSpecialTokenStrings:

    def test_endoftext_in_page(self) -> None:
        """A page containing '<|endoftext|>' tokenizes and chunks without error.

        disallowed_special=() prevents tiktoken from raising on strings
        that look like special tokens.
        """
        text = "Some text before <|endoftext|> and after the marker."
        pages = [_page(1, text)]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        assert len(chunks) == 1
        assert "<|endoftext|>" in chunks[0].text


# ---------------------------------------------------------------------------
# Non-ASCII and no-U+FFFD
# ---------------------------------------------------------------------------

class TestNonAscii:

    def test_non_ascii_chunks_without_error(self) -> None:
        """Non-ASCII text (accented, CJK, emoji) chunks cleanly."""
        text = "Héllo wörld café — 日本語テスト 🎉🚀 résumé naïve"
        pages = [_page(1, text)]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        assert len(chunks) >= 1
        # The original text should be preserved in the chunk.
        combined = "".join(c.text for c in chunks)
        assert "Héllo" in combined

    def test_no_replacement_character_in_chunks(self) -> None:
        """No chunk should contain U+FFFD (replacement character).

        This verifies that token-window decoding handles multi-byte
        character boundaries correctly.
        """
        # Build a long string with diverse scripts so chunking actually
        # splits it into multiple chunks.  Each repeated block is ~15
        # tokens, so 150 repetitions ≈ 2250 tokens → multiple chunks.
        block = "café résumé naïve 日本語 🎉🚀 مرحبا "
        long_text = block * 150
        pages = [_page(1, long_text)]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        assert len(chunks) >= 2, "Need multiple chunks to test boundaries"
        for chunk in chunks:
            assert "\ufffd" not in chunk.text, (
                f"Chunk {chunk.chunk_index} contains U+FFFD: "
                f"...{chunk.text[:80]}..."
            )

    def test_emoji_no_replacement(self) -> None:
        """Emoji-heavy text produces no U+FFFD in any chunk."""
        # Mix of multi-byte emoji (4-byte UTF-8) with ASCII
        block = "Hello 🎉 world 🌍 test 🚀 data 🔥 cool 😎 "
        long_text = block * 80  # ~800+ tokens
        pages = [_page(1, long_text)]
        chunks = chunk_pages(pages, max_tokens=500, overlap_tokens=50)

        assert len(chunks) >= 2
        for chunk in chunks:
            assert "\ufffd" not in chunk.text, (
                f"Chunk {chunk.chunk_index} contains U+FFFD"
            )
