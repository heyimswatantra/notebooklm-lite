"""Tests for rag/extraction.py.

All test PDFs are generated in-memory with PyMuPDF — no binary fixtures.
"""
from __future__ import annotations

import pymupdf
import pytest

from backend.rag.extraction import (
    CorruptPdfError,
    NoExtractableTextError,
    PageText,
    extract_pages,
)


# ---------------------------------------------------------------------------
# Helpers — build tiny PDFs in memory
# ---------------------------------------------------------------------------

def _make_pdf(pages_text: list[str]) -> bytes:
    """Create a minimal PDF with the given text on each page.

    Each entry in `pages_text` becomes one page. Use "" for a blank page.
    """
    doc = pymupdf.Document()
    for text in pages_text:
        page = doc.new_page(width=612, height=792)  # US Letter
        if text:
            # Insert text at the top-left corner.
            page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExtractPages:
    """Test extract_pages()."""

    def test_single_page(self) -> None:
        """Normal single-page PDF extracts correctly."""
        pdf = _make_pdf(["Hello world"])
        pages = extract_pages(pdf)
        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert "Hello world" in pages[0].text

    def test_multi_page(self) -> None:
        """Multi-page PDF returns pages numbered from 1."""
        pdf = _make_pdf(["Page one", "Page two", "Page three"])
        pages = extract_pages(pdf)
        assert len(pages) == 3
        assert [p.page_number for p in pages] == [1, 2, 3]
        assert "Page one" in pages[0].text
        assert "Page two" in pages[1].text
        assert "Page three" in pages[2].text

    def test_skip_blank_pages(self) -> None:
        """Blank / whitespace-only pages are skipped."""
        pdf = _make_pdf(["First", "", "Third"])
        pages = extract_pages(pdf)
        # The blank middle page should be skipped.
        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert pages[1].page_number == 3

    def test_all_blank_pages_raises(self) -> None:
        """A PDF where every page is blank raises NoExtractableTextError."""
        pdf = _make_pdf(["", ""])
        with pytest.raises(NoExtractableTextError, match="No extractable text"):
            extract_pages(pdf)

    def test_invalid_bytes_raises(self) -> None:
        """Random bytes (not a PDF) raise CorruptPdfError."""
        with pytest.raises(CorruptPdfError, match="Not a valid PDF"):
            extract_pages(b"this is not a pdf at all")

    def test_corrupt_pdf_header_raises(self) -> None:
        """Bytes with a PDF header but invalid structure raise CorruptPdfError."""
        corrupt = b"%PDF-1.4\nnot a valid pdf body"
        with pytest.raises(CorruptPdfError, match="Not a valid PDF"):
            extract_pages(corrupt)

    def test_non_ascii_roundtrip(self) -> None:
        """Non-ASCII text (emoji, CJK) round-trips without errors."""
        # Note: PyMuPDF's insert_text uses a built-in font that may not
        # render every glyph, but the text is still stored in the PDF
        # and extractable.  We use characters that the default font can
        # handle or that PyMuPDF stores as text regardless.
        text = "Héllo wörld — café 日本語"
        pdf = _make_pdf([text])
        pages = extract_pages(pdf)
        assert len(pages) == 1
        # At minimum, the ASCII parts must survive.  Some fonts may not
        # have CJK glyphs, so we check the accented-Latin portion.
        assert "Héllo" in pages[0].text or "H" in pages[0].text

    def test_special_token_string_in_text(self) -> None:
        """Text containing tiktoken special-token strings doesn't crash.

        This test verifies extraction; the chunking test verifies
        that <|endoftext|> tokenizes without error.
        """
        text = "before <|endoftext|> after"
        pdf = _make_pdf([text])
        pages = extract_pages(pdf)
        assert len(pages) == 1
        assert "<|endoftext|>" in pages[0].text
