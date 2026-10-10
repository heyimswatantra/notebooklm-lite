# NotebookLM Lite
Personal RAG learning project: upload PDFs, ask questions, get cited answers.

## Quickstart
1. cp .env.example .env  (add GEMINI_API_KEY and VOYAGE_API_KEY, set CHAT_MODEL and EMBED_MODEL)
2. docker compose up --build
3. Smoke test: docker compose exec backend python scripts/smoke_test.py
4. Backend: http://localhost:8000/docs · Frontend: http://localhost:5173

## Docs
SPEC.md · ARCHITECTURE.md · ROADMAP.md · DECISIONS.md · EXPERIMENTS.md · AGENTS.md

## Status
See ROADMAP.md for the current milestone.