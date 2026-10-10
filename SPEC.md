# Product Specification

## Overview

A personal document Q&A application inspired by NotebookLM.

Users create notebooks, upload PDF documents, and ask questions
about the documents.

Answers should be grounded in the uploaded documents and provide
citations to the relevant source chunks/pages.

## User

The initial version has one user: the project owner.

Authentication and multi-user support are out of scope.

## Core Concepts

### Notebook

A collection of documents that can be queried together.

### Document

A PDF uploaded to a notebook.

### Chunk

A piece of extracted document text used for retrieval.

Each chunk has:
- document
- page number
- text
- embedding

## Core User Flow

1. Create/select a notebook.
2. Upload a PDF.
3. System extracts text from each page.
4. System splits text into chunks.
5. System generates embeddings.
6. Chunks and embeddings are stored.
7. User asks a question.
8. Question is embedded.
9. System retrieves relevant chunks.
10. LLM generates an answer using those chunks.
11. Answer contains citations.
12. User can inspect cited source chunks.

## Functional Requirements

### Notebooks

- Create notebook
- List notebooks
- Select notebook

### Documents

- Upload PDF to notebook
- Extract text
- Store document metadata
- Store chunks
- Store embeddings

### Chat

- Ask question within notebook
- Retrieve top-k relevant chunks
- Generate grounded answer
- Return citations
- Return source chunks

### Logging

For every question:
- question
- retrieved chunks
- retrieval scores
- answer
- citations
- model, token counts, latency

## Answer Behavior

The model should:

- answer only from supplied context
- cite supporting chunks
- avoid unsupported claims
- say that the answer was not found when context is insufficient

## Edge Cases

- Non-PDF upload → 400 with a clear message
- PDF with no extractable text (scanned) → rejected with a clear message
- Maximum upload size: 20 MB
- Each question is independent (no conversation history)
- Deleting notebooks/documents is out of scope for Phase 1

## Out of Scope — Phase 1

- Authentication
- Multi-user support
- Multiple file formats
- Web search
- Hybrid retrieval
- Reranking
- Agents
- Conversation memory
- Advanced UI
- Production deployment
