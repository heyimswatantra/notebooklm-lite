# Roadmap


## Phase 1 — Working RAG

### Milestones (work one at a time; stop after each)

- **M1** Compose up: Postgres+pgvector, FastAPI /health. `llm/` interface, fake providers, and config in place, with a smoke test that embeds one string and gets one chat reply. *Verify: curl + smoke test*
- **M2** Schema + migrations (plain SQL files). *Verify: psql*
- **M3** Ingestion: upload → extract → chunk → embed → store. *Verify: row counts*
- **M4** Retrieval: question → top-k chunks + scores. *Verify: curl*
- **M5** Generation: grounded prompt, citations, query_logs. *Verify: curl + log row*
- **M6** React UI: notebooks, upload, chat, citation view
- **M7** Observability

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
- [ ] PyMuPDF extraction
- [ ] Chunking
- [ ] scripts/inspect_chunks.py (print chunks of a local PDF; no DB, no API)
- [ ] PDF upload endpoint
- [ ] Embedding
- [ ] Storage
- [ ] GET /notebooks/{id}/documents

### M4 — Retrieval
- [ ] Question embedding
- [ ] Vector similarity search
- [ ] Notebook filtering
- [ ] Top-k retrieval

### M5 — Generation
- [ ] Context construction
- [ ] Grounded prompt
- [ ] Citations
- [ ] Source chunks

### M6 — UI
- [ ] React/Vite scaffold
- [ ] Notebook list
- [ ] Upload
- [ ] Chat
- [ ] Citation inspection

### M7 — Observability
- [ ] Log questions
- [ ] Log retrieved chunks
- [ ] Log scores
- [ ] Log answers

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



