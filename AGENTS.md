# AGENTS.md

## Project

This is a personal learning project implementing a document Q&A /
RAG system similar to NotebookLM.

The project is intentionally built from relatively low-level
components so that I can understand how RAG works and how retrieval
quality affects evaluation.

## Primary Goal

The goal is not to build the most production-ready RAG system.

The goal is to understand:

- PDF ingestion
- chunking
- embeddings
- vector retrieval
- context construction
- grounded generation
- citations
- RAG evaluation
- retrieval experiments

Prefer simple, explicit implementations over abstractions that hide
these concepts.

## User Skill Level

The project owner is experienced with software development and
React/TypeScript/Postgres/Docker but is not fluent in Python.

When introducing non-obvious Python:
- prefer straightforward Python
- avoid clever abstractions
- explain unfamiliar Python patterns
- use type hints
- keep functions small and understandable

## Technology

Backend:
 Backend:
- Python 3.12, managed with uv: `backend/pyproject.toml` + `backend/uv.lock` (both committed). Add dependencies with `uv add` only after asking; No pip, requirements.txt, or Poetry.
- FastAPI (plain synchronous `def` endpoints, not async, unless asked; ADR-007)
- PostgreSQL
- pgvector (psycopg v3 + raw SQL, no ORM; ADR-004)
- PyMuPDF

Frontend:
- React
- TypeScript
- Vite

Infrastructure:
- Docker Compose

## RAG Architecture

Do NOT introduce LangChain or LlamaIndex unless explicitly requested.

The initial RAG pipeline should remain explicit:

PDF
→ text extraction
→ chunking
→ embedding
→ pgvector
→ retrieval
→ context construction
→ LLM
→ cited answer

## LLM Abstraction

All LLM and embedding calls must go through the project's
LLM abstraction.

Do not scatter provider-specific API calls throughout the codebase.

The abstraction should make it possible to replace the provider
with LiteLLM later.

### Interface (backend/llm/base.py)

Use dataclasses for data and `typing.Protocol` for the provider interfaces.
A Protocol is Python's version of a TypeScript interface:
any class with matching methods satisfies it, no inheritance needed.
  
  ```python
    @dataclass(frozen=True)
    class ChatMessage:
        role: Literal["system", "user", "assistant"]
        content: str

    @dataclass(frozen=True)
    class ChatResult:
        text: str
        model: str
        prompt_tokens: int
        completion_tokens: int

    @dataclass(frozen=True)
    class EmbedResult:
        vectors: list[list[float]]
        model: str
        dimension: int

    class LLMError(Exception): ...
    class LLMRateLimitError(LLMError): ...
    class LLMAuthError(LLMError): ...

    class ChatProvider(Protocol):
        def chat(self, messages: list[ChatMessage], *,
                  temperature: float = 0.0) -> ChatResult: ...

    class EmbeddingProvider(Protocol):
        def embed(self, texts: list[str], *,
                  kind: Literal["document", "query"]) -> EmbedResult: ...
  ```

### Rules

- gemini.py implements ChatProvider; voyage.py implements EmbeddingProvider.
  Each maps our types to its SDK/API (e.g. Gemini's role names and
  system-instruction handling) and back. That mapping stays inside the file.
- factory.py exposes get_chat_provider() and get_embedding_provider(),
  chosen by config. No other module imports gemini.py or voyage.py.
- Provider SDK exceptions are caught inside llm/ and re-raised as our
  LLMError types. Rate limits get retry with exponential backoff
  (max 3 attempts) inside the provider.
- embed() splits large inputs into batches internally and returns
  vectors in input order.
- Return token counts in every result so services/ can log them.
- embed() must verify len(vector) == EMBED_DIMENSION and raise LLMError
  otherwise.
- App startup checks that the chunks.embedding column dimension equals
  EMBED_DIMENSION and fails with a clear message if not.
- Tests use FakeChatProvider / FakeEmbeddingProvider (in tests/). Tests
  must never call real APIs.
- The one exception is `scripts/smoke_test.py`: run manually (not by pytest),
  it makes one real embed() call and one real chat() call to verify API keys
  and model names.

### Config (backend/config.py)

Read all settings from environment variables in one place, one frozen
Settings object, created once at startup. Nothing else reads os.environ.

## Approved Dependencies

Already declared in pyproject.toml: fastapi, uvicorn, psycopg (v3), pgvector,
pymupdf, tiktoken, pydantic-settings, python-multipart, google-genai, voyageai;
dev: pytest, httpx. Ask before adding anything else.

## Retrieval

Initial retrieval should be simple vector similarity search
using pgvector.

Do not introduce hybrid search, reranking, query expansion,
agents, or other retrieval techniques unless explicitly requested.

## Evaluation

Evaluation is a first-class concern.

Important RAG behavior should remain observable and testable.

Log:
- question
- retrieved chunk IDs
- retrieved scores
- generated answer
- citations
- model name, prompt/completion tokens, latency
- relevant request metadata

## Architecture Rules

Keep these concerns separate:

- API
- document ingestion
- chunking
- embeddings
- retrieval
- generation
- database access

Do not create unnecessary abstractions.

+## Frontend

- React + TypeScript (strict) + Vite. No router, UI kit, CSS framework, state
  or data-fetching library unless asked. Styling: CSS Modules + CSS variables
  (tokens from DESIGN.md).
- All backend calls go through one typed client (src/api/client.ts); types
  mirror the backend responses. Components never call fetch directly.
- Use only existing backend endpoints. Do not change the backend for the UI
  unless asked.
- Checks: `npm run build` (includes tsc) and `npm run lint` must pass.
- Quality floor: responsive down to phone width, visible keyboard focus,
  labelled inputs, reduced motion respected, aria-live for upload status.

## Development Rules

At the start of every session, read SPEC.md, ARCHITECTURE.md, ROADMAP.md
and DECISIONS.md (and DESIGN.md for frontend work).
Work on ONE roadmap milestone at a time, then stop and wait for my review.

Before implementing a significant feature:

1. Inspect the existing architecture.
2. Explain the proposed change.
3. Identify affected files.
4. Implement the smallest useful version.
5. Run tests (pytest). Add at least one test per new behavior.
6. Tick the ROADMAP checkbox and record any new decision in DECISIONS.md.
7. Report what changed and how I can verify it manually.

Do not refactor unrelated code while implementing a feature.

Do not silently introduce new frameworks or dependencies.

If a requirement is ambiguous, ask rather than inventing
significant behavior.

## Secrets and Config

- API keys live in `.env` (gitignored). Commit only `.env.example`.
- Never hardcode API keys, model names or embedding dimensions; read them from config.

## Learning Rule

When there are two reasonable implementations, prefer the one
that makes the underlying RAG concept easier to understand.

Avoid hiding important RAG behavior behind framework abstractions.
