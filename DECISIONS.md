# Architecture Decisions

## ADR-001 — No LangChain Initially

### Decision

Do not use LangChain or LlamaIndex in Phase 1.

### Reason

The goal is to understand the RAG pipeline directly.

### Reconsider When

After the baseline implementation and evaluation system
are working.

---

## ADR-002 — PostgreSQL + pgvector

### Decision

Use PostgreSQL with pgvector for vector storage.

### Reason

The project already uses PostgreSQL and this avoids introducing
a separate vector database.

---

## ADR-003 — LLM Provider Abstraction

### Decision

All LLM and embedding calls go through a thin internal abstraction.

### Reason

Phase 6 should allow introducing LiteLLM without rewriting
the application.

---

## ADR-004 — psycopg + raw SQL, no ORM

### Decision
psycopg + raw SQL, no ORM

### Reason
SQL is already familiar; avoids hiding queries (including pgvector ops).

---

## ADR-005 — Embedding model and dimension

### Decision

Voyage AI. Fix the dimension at 1024 and pass it to the provider explicitly. Model: voyage-4-lite

### Reason
schema depends on N. Changing models later requires re-embedding.

---

## ADR-006 — Chunks do not cross page boundaries

### Decision

Chunks do not cross page boundaries

### Reason
exact page citations. Trade-off: loses context at page breaks. Reconsider in Phase 2/3 experiments.

---

## ADR-007 — Synchronous ingestion and endpoints

### Decision

Synchronous ingestion and endpoints

### Reason
simplest to read and debug. Reconsider in Phase 7.

---

## ADR-008 — Provider-agnostic by interface, not by lowest common denominator

### Decision

chat and embedding providers are separate, config-selected
implementations behind small interfaces. No provider-specific features
(e.g. Gemini grounding, provider-side caching) outside llm/.

### Reason
lets LiteLLM replace llm/ in Phase 6 without touching rag/ or services/.

## ADR-009 — Migrations

### Decision
Numbered .sql files in backend/db/migrations/, applied in order by
scripts/migrate.py, which records applied files in a schema_migrations table.

### Reason
Simple and visible; no migration framework to learn. Reconsider if the schema
churns a lot.

## ADR-010 — uv for Python dependency management

### Decision
uv with pyproject.toml and a committed uv.lock. Dependencies declared by me
before M1; the agent adds nothing without asking.

### Reason
Reproducible installs, fast Docker builds, one tool for Python and deps.

## ADR-011 — Use generate_content, not interactions API

### Decision
Use `client.models.generate_content()` from the google-genai SDK for all
chat completions. Do not use the newer `client.interactions.create()` API.

### Reason
Our ChatProvider.chat() is stateless: we pass the full message list on every
call, and SPEC.md says each question is independent (no conversation memory).
generate_content fits that model directly. The interactions API is designed
for stateful, multi-turn conversations with server-side storage, which adds
complexity we don't need. If conversation memory is added later, we can still
pass history through chat(). Treat interactions as out of scope unless a
later phase explicitly needs it.