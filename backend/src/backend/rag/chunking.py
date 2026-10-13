"""Token-based text chunking for RAG.

Splits extracted pages into overlapping chunks of approximately
`max_tokens` tokens. Chunks never cross page boundaries (ADR-006)
so that page citations remain exact.

Token counting uses tiktoken's cl100k_base encoding. This is NOT the
same tokenizer that Voyage AI uses — Voyage publishes its own tokenizer
(voyageai.Client().tokenize() / count_tokens(), and open-source on
HuggingFace). We use cl100k_base here because it's fast, local, and
good enough for approximate chunk sizing. The exact token count does
not matter for chunking; only the approximate size matters.

NOTE: batch-size / rate-limit logic in voyage.py must NOT rely on
cl100k_base counts. Use Voyage's own count_tokens() for that.
"""
from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from backend.rag.extraction import PageText

# Module-level encoder — created once, reused across calls.
# cl100k_base is the encoding used by GPT-4 / text-embedding-ada-002.
# It approximates, but is not, Voyage's tokenizer (see module docstring).
_ENC = tiktoken.get_encoding("cl100k_base")


@dataclass(frozen=True)
class Chunk:
    """One chunk of document text."""
    chunk_index: int    # 0-based, sequential across the entire document
    page_number: int    # which page this chunk came from (1-based)
    text: str
    token_count: int    # number of tokens in this chunk's window


def _decode_token_window(
    all_tokens: list[int], start: int, end: int
) -> str:
    """Decode tokens[start:end] to clean UTF-8 text (no U+FFFD).

    In rare cases a token boundary can fall inside a multi-byte UTF-8
    character (happens with cl100k_base byte-level fallback tokens for
    uncommon characters). When that occurs, we extend ``end`` or advance
    ``start`` by up to 3 tokens to snap to a valid character boundary.

    This is safe because:
    - The full page text is valid UTF-8, so a boundary always exists
      within a few tokens.
    - Overlap between chunks means any characters adjusted away from
      one chunk's edge will appear in an adjacent chunk.
    """
    total = len(all_tokens)

    # Fast path (covers 99%+ of cases): the exact window decodes cleanly.
    raw = _ENC.decode_bytes(all_tokens[start:end])
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # Slow path: try small adjustments to find a clean decode.
    # Prefer extending end (adds content) over advancing start (drops overlap).
    for delta_end in range(4):
        for delta_start in range(4):
            if delta_end == 0 and delta_start == 0:
                continue  # already tried
            s = start + delta_start
            e = end + delta_end
            if s >= e or e > total:
                continue
            raw = _ENC.decode_bytes(all_tokens[s:e])
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                continue

    # Should never reach here with valid input. Drop partial bytes
    # rather than emitting U+FFFD.
    raw = _ENC.decode_bytes(all_tokens[start:end])
    return raw.decode("utf-8", errors="ignore")


def chunk_pages(
    pages: list[PageText],
    *,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """Split extracted pages into overlapping token-based chunks.

    Args:
        pages: Output of extract_pages().
        max_tokens: Target maximum tokens per chunk (default 500).
        overlap_tokens: Number of tokens to repeat between consecutive
            chunks on the same page (default 50).

    Returns:
        List of Chunk, with chunk_index numbered 0, 1, 2, … across the
        entire document. Chunks never cross page boundaries. Empty or
        whitespace-only pages produce no chunks.
    """
    stride = max_tokens - overlap_tokens  # how far to advance each step
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            # Defensive: extract_pages already skips blank pages,
            # but if called with hand-built PageText, skip gracefully.
            continue

        # Encode to tokens.  disallowed_special=() allows strings like
        # "<|endoftext|>" that appear in some PDFs to be encoded normally
        # instead of raising a tiktoken error.
        tokens = _ENC.encode(text, disallowed_special=())
        n = len(tokens)

        # Short page: fits in a single chunk.
        if n <= max_tokens:
            chunks.append(Chunk(chunk_index, page.page_number, text, n))
            chunk_index += 1
            continue

        # Sliding window.  We advance by `stride` tokens each step.
        # Each window is at most `max_tokens` tokens.
        # Stop as soon as a window reaches the end of the page.
        start = 0
        while start < n:
            end = min(start + max_tokens, n)
            window_text = _decode_token_window(tokens, start, end)
            token_count = end - start   # window length in tokens

            chunks.append(Chunk(chunk_index, page.page_number, window_text, token_count))
            chunk_index += 1

            # This window reached the end — no more chunks for this page.
            if end >= n:
                break

            start += stride

    return chunks
