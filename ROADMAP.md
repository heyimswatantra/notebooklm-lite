# Roadmap


## Phase 1 — Working RAG

### Milestones (work one at a time; stop after each)

- **M1** Compose up: Postgres+pgvector, FastAPI /health. `llm/` interface, fake providers, and config in place, with a smoke test that embeds one string and gets one chat reply. *Verify: curl + smoke test*
- **M2** Schema + migrations (plain SQL files). *Verify: psql*
- **M3** Ingestion: upload → extract → chunk → embed → store. *Verify: row counts*
- **M4** Retrieval: question → top-k chunks + scores. *Verify: curl*
- **M5** Generation: grounded prompt, citations, query_logs. *Verify: curl + log row*
- **M6** React UI: notebooks, upload, chat, citation view

### M1 — Infrastructure
- [x] Repository setup
- [x] Dockerfile for backend using uv (`uv sync --frozen`, venv on PATH so `python` and `pytest` work inside the container)
- [x] Docker Compose
- [x] PostgreSQL
- [x] pgvector
- [x] FastAPI
- [x] `llm/` interface (base, gemini, voyage, factory), fake providers, config
- [x] Smoke test: embeds one string and gets one chat reply (verifies both API keys)

### M2 — Data
- [x] Migration runner (scripts/migrate.py + schema_migrations table)
- [x] notebooks table
- [x] documents table
- [x] chunks table
- [x] query_logs table  
- [x] Startup check: chunks.embedding dimension == EMBED_DIMENSION
- [x] POST /notebooks, GET /notebooks

### M3 — Ingestion
- [x] PyMuPDF extraction
- [x] Chunking
- [x] scripts/inspect_chunks.py (print chunks of a local PDF; no DB, no API)
- [x] PDF upload endpoint
- [x] Embedding
- [x] Storage
- [x] GET /notebooks/{id}/documents

### M4 — Retrieval
- [x] Question embedding
- [x] Vector similarity search
- [x] Notebook filtering
- [x] Top-k retrieval
- [x] POST /notebooks/{id}/retrieve (inspection endpoint; M5 reuses the service)

### M5a — Context and prompt (pure functions, no model calls)
- [x] Context construction
- [x] Grounded prompt
- [x] scripts/show_prompt.py (print the exact prompt for a question; no chat call)

### M5b — Answer endpoint, citations, logging
- [x] POST /notebooks/{id}/chat
- [x] Citations (parse, validate, map to chunks)
- [x] Source chunks in the response
- [x] Short-circuit with "not found" when nothing is retrieved

### M5b — Observability
- [x] Log questions
- [x] Log retrieved chunks
- [x] Log scores
- [x] Log answers

### M6 — UI
- [ ] React/Vite scaffold
- [ ] Notebook list
- [ ] Upload
- [ ] Chat
- [ ] Citation inspection

### Phase 1 Exit Criteria

- [ ] Upload 2–3 PDFs
- [ ] Ask questions
- [ ] Receive grounded answers
- [ ] Answers contain citations
- [ ] Citations open source chunks
- [ ] Retrieval information is logged

---

## Phase 2 — Evaluation

- [ ] Create evaluation dataset
- [ ] Record questions with expected answers/context
- [ ] Introduce RAGAS
- [ ] Evaluate retrieval quality
- [ ] Evaluate answer quality
- [ ] Compare chunking strategies
- [ ] Compare retrieval parameters
- [ ] Make chunk size/overlap configurable and record them per experiment

---

## Phase 3 — Retrieval Improvements

Potential experiments:

- [ ] Chunk size
- [ ] Chunk overlap
- [ ] Top-k
- [ ] Metadata filtering
- [ ] Hybrid search
- [ ] Reranking

---

## Phase 4 — Guardrails & Security
- [ ] PII redaction on ingestion
- [ ] Prompt-injection test (malicious text inside a PDF) and mitigation
- [ ] Output checks, audit log

---

## Phase 5 — Tokenomics & Latency
- [ ] Streaming responses
- [ ] Prompt caching / semantic cache
- [ ] Cost per request, small vs large model routing

---

## Phase 6 — LLM Gateway

- [ ] Introduce LiteLLM
- [ ] Multiple model providers
- [ ] Model configuration
- [ ] Cost/latency tracking
- [ ] Fallbacks and retries

---

## Phase 7 — Deployment
- [ ] Dockerized app on Cloud Run
- [ ] CI pipeline
- [ ] Prompt rollback
- [ ] Better error handling
- [ ] Better observability
- [ ] Performance improvements
- [ ] Background ingestion
- [ ] Better UI



