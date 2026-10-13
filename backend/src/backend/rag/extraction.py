"""PDF text extraction using PyMuPDF.

Extracts text from each page of a PDF. Pages with no extractable text
(whitespace-only) are skipped.
"""
from __future__ import annotations

from dataclasses import dataclass

import pymupdf  # PyMuPDF


@dataclass(frozen=True)
class PageText:
    """One page of extracted text."""
    page_number: int   # 1-based (first page is 1)
    text: str


class ExtractionError(Exception):
    """Raised when a PDF cannot be processed."""


def extract_pages(pdf_bytes: bytes) -> list[PageText]:
    """Extract text from every page of a PDF.

    Args:
        pdf_bytes: Raw bytes of a PDF file.

    Returns:
        List of PageText, one per page that has extractable text.
        Pages are numbered from 1.

    Raises:
        ExtractionError: If the bytes are not a valid PDF or if no page
            contains extractable text (e.g. a scanned/image-only PDF).
    """
    # Open the PDF from raw bytes.
    # pymupdf.Document(stream=...) raises an exception if the bytes
    # are not a valid PDF.
    try:
        doc = pymupdf.Document(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ExtractionError(f"Not a valid PDF: {exc}") from exc

    pages: list[PageText] = []

    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text()

        # Skip pages that are blank or whitespace-only
        if not text or not text.strip():
            continue

        pages.append(PageText(page_number=i + 1, text=text))

    doc.close()

    if not pages:
        raise ExtractionError(
            "No extractable text found. The PDF may be scanned or image-only."
        )

    return pages
