CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE notebooks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE documents (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    notebook_id bigint NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    filename text NOT NULL,
    page_count integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    page_number integer NOT NULL,
    text text NOT NULL,
    embedding vector(1024) NOT NULL,
    embedding_model text NOT NULL,
    CONSTRAINT uq_chunks_document_chunk_index UNIQUE (document_id, chunk_index)
);

CREATE TABLE query_logs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    notebook_id bigint NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    question text NOT NULL,
    retrieved_chunk_ids bigint[] NOT NULL,
    scores double precision[] NOT NULL,
    answer text NOT NULL,
    citations jsonb NOT NULL,
    model text NOT NULL,
    prompt_tokens integer NOT NULL,
    completion_tokens integer NOT NULL,
    latency_ms integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_notebook_id ON documents(notebook_id);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
