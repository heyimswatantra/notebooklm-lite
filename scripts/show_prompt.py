#!/usr/bin/env python3
"""Print the grounded prompt for a notebook question (retrieval + prompt only).

Usage:
    uv run python scripts/show_prompt.py <notebook_id> "<question>" [--k 5]

Runs real embedding + DB retrieval; does not call the chat provider.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from backend.config import get_settings
from backend.db.connection import get_connection
from backend.llm.factory import get_embedding_provider
from backend.rag.prompting import PROMPT_VERSION, build_messages
from backend.services.errors import NotebookNotFoundError
from backend.services.retrieval import retrieve_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Show grounded prompt for a question")
    parser.add_argument("notebook_id", type=int)
    parser.add_argument("question", type=str)
    parser.add_argument("--k", type=int, default=5, help="Number of chunks to retrieve")
    args = parser.parse_args()

    settings = get_settings()
    embedder = get_embedding_provider(settings)

    conn = get_connection()
    try:
        try:
            chunks = retrieve_chunks(
                conn,
                args.notebook_id,
                args.question,
                embedder=embedder,
                k=args.k,
            )
        except NotebookNotFoundError:
            print(f"Notebook not found: {args.notebook_id}", file=sys.stderr)
            sys.exit(1)

        if not chunks:
            print("No chunks retrieved; M5b would short-circuit without calling build_messages.")
            sys.exit(0)

        built = build_messages(args.question, chunks)

        print(f"prompt_version={PROMPT_VERSION}")
        print(f"retrieved={len(chunks)} chunk(s)")
        print("-" * 72)
        for msg in built.messages:
            print(f"--- role: {msg.role} ---")
            print(msg.content)
            print()
        print("-" * 72)
        print("label_to_chunk_id:")
        for label in sorted(built.label_to_chunk_id):
            print(f"  [{label}] -> {built.label_to_chunk_id[label]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
