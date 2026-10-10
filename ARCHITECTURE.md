# Architecture

## High-Level Flow

                         ┌─────────────┐
                         │   React UI  │
                         └──────┬──────┘
                                │
                              HTTP
                                │
                         ┌──────▼──────┐
                         │   FastAPI   │
                         └──────┬──────┘
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
              Ingestion                      Chat
                 │                            │
          ┌──────▼──────┐              ┌──────▼──────┐
          │   PyMuPDF   │              │  Retrieval  │
          └──────┬──────┘              └──────┬──────┘
                 │                            │
              chunks                       pgvector
                 │                            │
                 └──────────────┬─────────────┘
                                │
                           ┌────▼────┐
                           │   LLM   │
                           └─────────┘

## Backend Layers

backend/
    api/
        HTTP endpoints

    services/
        orchestration only: ingest_document(), answer_question()
        (calls rag/, db/, llm/; contains no RAG logic itself)

     
    rag/
        extraction.py   (PyMuPDF)
        chunking.py
        retrieval.py
        prompting.py    (context construction + citation parsing)
 
 
    db/
        database connection
        queries/models

    llm/
        base.py       ChatProvider / EmbeddingProvider (typing.Protocol)
        gemini.py     implements chat()
        voyage.py     implements embed()
        factory.py    builds providers from config

        chat(messages, *, temperature) -> ChatResult(text, prompt_tokens, completion_tokens, model)
        embed(texts, *, kind: "document" | "query") -> EmbedResult(vectors, model, dimension)

        Rules: no provider SDK imports outside llm/. Providers are chosen by
        env vars (CHAT_PROVIDER, EMBED_PROVIDER, *_MODEL), never in code.
        Provider-specific errors are translated to our own LLMError types.

## Repository Layout

  backend/        (pyproject.toml, uv.lock, api/, services/, rag/, db/, llm/, config.py, main.py, tests/)  
  backend/db/migrations/   (numbered .sql files: 001_init.sql, ...)
  frontend/       (React + Vite + TS)
  scripts/        (smoke_test.py, migrate.py)
  docker-compose.yml, .env.example, .gitignore, and the 7 docs

## Data Model

notebooks(id, name, created_at)
documents(id, notebook_id, filename, page_count, created_at)
chunks(id, document_id, chunk_index, page_number, text,
       embedding vector(1024), embedding_model)
query_logs(id, notebook_id, question, retrieved_chunk_ids, scores,
           answer, citations, model, prompt_tokens, completion_tokens,
           latency_ms, created_at)

The dimension (1024) comes from ADR-005 and must match EMBED_DIMENSION.
Store embedding_model per chunk so experiments stay comparable.

## Important Boundary

The RAG pipeline should remain understandable:

chunk
→ embed
→ store
→ retrieve
→ construct context
→ generate

Do not hide this pipeline behind a third-party RAG framework.

## Initial Retrieval
 
Vector similarity search.
 
Parameters:
k = 5
Metric: cosine distance (`<=>`), score = 1 - distance.
No vector index in Phase 1; exact scan is fine at this scale.
 
Search is scoped to the selected notebook.

## Citations

Context chunks are labeled [1]..[k]. The model cites by label; the backend maps labels to chunk IDs and drops any label not in the retrieved set.

## Chunking

Initial strategy:

- approximately 500 tokens
- approximately 50 token overlap
- chunks never cross page boundaries (keeps page citations exact)
- tokens counted with tiktoken (approved dependency)

The chunking implementation must be isolated so that different
strategies can be compared later.

## LLM

All model calls go through the `llm/` package (see Backend Layers above).

Provider-specific implementation must not leak into the rest
of the application.

## Future

Possible future improvements:

- hybrid search
- reranking
- improved chunking
- query rewriting
- LiteLLM
- RAGAS evaluation
