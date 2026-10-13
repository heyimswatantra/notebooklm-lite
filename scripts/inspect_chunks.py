#!/usr/bin/env python3
"""Inspect chunks from a local PDF file.

Usage:
    uv run python scripts/inspect_chunks.py <path-to-pdf>

Prints per chunk: index, page number, token count, and first ~100 chars.
No database, no API calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add the backend src directory to the path so we can import the rag package.
# This is a standalone script, not part of the installed package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from backend.rag.chunking import chunk_pages
from backend.rag.extraction import ExtractionError, extract_pages


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/inspect_chunks.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    pdf_bytes = pdf_path.read_bytes()

    try:
        pages = extract_pages(pdf_bytes)
    except ExtractionError as exc:
        print(f"Extraction error: {exc}")
        sys.exit(1)

    print(f"Extracted {len(pages)} page(s) with text.\n")

    chunks = chunk_pages(pages)

    print(f"Produced {len(chunks)} chunk(s).\n")
    print("-" * 72)

    for chunk in chunks:
        # Show the first ~100 characters, replacing newlines with spaces
        # for readability.
        preview = chunk.text[:100].replace("\n", " ")
        if len(chunk.text) > 100:
            preview += "…"

        print(
            f"[{chunk.chunk_index:>4}]  "
            f"page {chunk.page_number:<4}  "
            f"{chunk.token_count:>5} tokens  "
            f"{preview}"
        )

    print("-" * 72)


if __name__ == "__main__":
    main()
