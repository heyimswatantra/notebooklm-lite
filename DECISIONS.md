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

---

## ADR-012 — tiktoken (cl100k_base) for chunk-size token counting

### Decision

Use tiktoken's cl100k_base encoding for counting tokens when splitting
text into chunks. This is NOT Voyage's tokenizer.

Voyage AI publishes its own tokenizer:
- `voyageai.Client().tokenize(texts, model=...)` — returns token lists
- `voyageai.Client().count_tokens(texts, model=...)` — returns total count
- Open-source on HuggingFace (`voyageai/voyage-4-large` etc.)

Voyage token counts are ~1.1–1.2× higher than cl100k_base equivalents.

### Reason

For chunking, only the approximate size matters: we want roughly 500-token
chunks, not exactly 500 Voyage tokens. cl100k_base is fast, local (no API
call), and available as an already-approved dependency (tiktoken). The
slight count mismatch doesn't affect retrieval quality.

### Constraint

Batch-size and rate-limit logic in `voyage.py` must NOT rely on cl100k_base
counts. Use Voyage's own `count_tokens()` for TPM tracking there.

---

## ADR-013 — Retrieval query lives in db/chunks.py, not rag/retrieval.py

### Decision

The vector similarity search is a single SQL query using pgvector's `<=>`
operator. It lives in `db/chunks.py` alongside the existing chunk-insert
functions.  `rag/` is reserved for CPU-only, database-free transforms
(extraction, chunking).

### Reason

There is no pure-function RAG logic to separate out. The "retrieval" step
is just a parameterised SQL query — putting it in `db/` follows the
project rule "SQL only in db/".

### Reconsider When

Retrieval gains reranking, hybrid search, query rewriting, or any other
logic that is not a single database query.

---

## ADR-014 — Grounded prompt contract (M5a)

### Decision

- Retrieved chunks are labeled `[1]`..`[k]` in retrieval rank order in the
  user message context block.
- The model cites by those labels only (not page numbers or filenames in
  citations).
- When context is insufficient, the model must reply with exactly one fixed
  sentence (`NOT_FOUND_MESSAGE` in `rag/prompting.py`); M5b may also
  short-circuit without a model call when nothing is retrieved.
- Prompt rules are plain text in `SYSTEM_PROMPT`; no provider structured-output
  or JSON schema for citations in Phase 1.
- `PROMPT_VERSION` (`grounded-v1`) tags the contract for logging and later
  experiments.

### Reason

Keeps context construction and prompting as testable pure functions, aligns
with ARCHITECTURE citation mapping, and avoids locking Phase 1 to one
provider's response-format features.

---

## ADR-015 — Citation parsing (M5b)

### Decision

- Parse citation labels from model answer text in `rag/citations.py` via
  `parse_citations(answer_text, valid_labels)`.
- Accept bracket forms `[n]`, `[n][m]`, and `[n, m]` where each label is a
  positive integer (comma-separated inside one pair of brackets).
- Ignore non-citation brackets (e.g. `[sic]`, `[1-3]` ranges).
- Return cited labels in **first-appearance order**, deduplicated.
- Do **not** modify the answer text.

### Reason

Keeps parsing testable without DB or LLM fakes; matches the prompt contract
in ADR-014.

---

## ADR-016 — Invalid citation labels (M5b)

### Decision

- Labels parsed from the answer that are not in the retrieved set (`valid_labels`)
  are **dropped** from API `citations` and from the cited list in the response.
- They are recorded in `query_logs.citations` jsonb as `invalid_labels`.
- The model answer string stored and returned is unchanged.

### Reason

Prevents hallucinated chunk references while preserving the raw model output
for evaluation and debugging.

---

## ADR-017 — Vite dev proxy instead of CORS (M6a)

### Decision

Frontend requests to `/api/*` are proxied to the backend via Vite's dev server
proxy, stripping the `/api` prefix. No CORS headers or origins are configured on
the backend. The proxy target is configurable via an environment variable
(`API_PROXY_TARGET`), defaulting to `http://backend:8000`.

### Reason

Avoids coupling the backend to frontend development origins or weakening
security with permissive CORS policies. In production, a reverse proxy
(e.g., Nginx, Caddy, Cloud Run routing) can apply the same path rewrite.

---

## ADR-018 — No router, state, or data-fetching library (M6a)

### Decision

Do not use React Router, Redux/Zustand, or TanStack Query. Manage application
state with standard React hooks (`useState`, `useEffect`, custom hook
`useDocuments`) and coordinate all backend communication through a single
strongly-typed API client module (`src/api/client.ts`).

### Reason

The initial app is a single-screen document Q&A tool. Introducing routing or
external state management adds dependency overhead and indirection without
solving any problem present in Phase 1.

---

## ADR-019 — CSS Modules and CSS variables for styling (M6a)

### Decision

Use CSS Modules (`*.module.css`) for component-scoped styles alongside global
CSS custom properties (tokens defined in `src/tokens.css`). Do not use Tailwind,
CSS-in-JS, or component UI libraries.

### Reason

Maintains full control over typography, spacing, and tone steps as specified in
`DESIGN.md` with zero runtime CSS overhead and without pulling in large external
design systems or utility classes.
