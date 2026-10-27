# Experiments

Log every RAG experiment here. Keep the newest experiment first. Preserve baseline results so later changes can be compared against the same questions and configuration.

## Baselines

## Informal baseline (baseline-v0)

- Date: 25-10-2026
- Git commit: 9e4da2f
- Corpus: eRAG (Salemi & Zamani 2024), Seven Failure Points (Barnett et al. 2024); one notebook, both PDFs
- Config: chunk 500 tokens / 50 overlap, no cross-page chunks (ADR-006), voyage-4-lite 1024-dim, cosine, exact scan, k=5
- Method: questions written before running; relevant = chunk alone contains the answer

### Extraction notes (from inspect_chunks.py)
- (repeated headers? column order? tables? equations? references?)
- Repeated page headers - No
- arXiv stamp in middle of sentence - Yes
- Two-column text read in the wrong order - No
- Tables flattened into a stream of numbers - Yes
- Reference List becoming chunks - Yes

### Results
| ID | Type | Question (short) | Expected loc. | Rank of first relevant (k=5 / k=20) | Top-1 score | Relevant score | Result | Cause | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | Direct fact | On average, how many times faster is eRAG than end-to-end evaluation? | eRAG, runtime results paragraph (≈2.468×) | 1 | 0.672 | 0.672 | ✅ | - | - |
| Q2 | Direct fact | Which model was used as the default LLM in the eRAG experiments? | eRAG §3.1, experiment configuration (T5-small with FiD) | 3 | 0.532 | 0.495 | ✅ | - | First two chunks that outranked relevant are about LLM labelling documents with equation 1 and eRAG memory efficiency  respectively |
| Q3 | Conflicting facts | How many documents did the BioASQ experiment use? | 7FP intro/conclusion (15,000) vs §4.3 (4017). The paper disagrees with itself, so both chunks should come back. | 1 | 0.413 | 0.413 | ⚠️ | k (found only at a larger k), chunks 2-7 are mostly 7FP chunks that are only loosely related | both retrived but chunk with 15,000 was at rank 8  with score 0.311 |
| Q4 | Paraphrase | What goes wrong when someone asks about a topic the knowledge base touches on but never actually answers? | 7FP §5, FP1 Missing Content | 2 | 0.387 | 0.383| ✅ | - | outranked by FP2 Missed the Top Ranked Documents section chunk|
| Q5 | Paraphrase | Why not just have people label which passages are relevant when judging a retriever that feeds an LLM? | eRAG intro and §2 (human relevance judgments correlate weakly with downstream performance) | 1 | 0.540 | 0.540 | ✅ | - | Spans two chunks, second chunk at rand 2 with score 0.535 | 
| Q6 | List / completeness | List all seven failure points. | 7FP §5, FP1–FP7 (may span chunks; check all seven appear) | 1(all seven do appear) | 0.372 | 0.372 | ✅ | - | Spans two chunks, second chunk at rank 2 with score 0.325 | 
| Q7 | Table | How much GPU memory did end-to-end evaluation need on NQ compared with eRAG? | eRAG Table 2 (75.0 GB vs 4.9 / 1.5 GB) | 1 | 0.697 | 0.697 | ✅ | - | - |
| Q8 | Table | Which failure points does the lesson about continuous calibration relate to? | 7FP Table 2 (FP2–7) | 1 | 0.340 | 0.340 | ✅ | - | - |
| Q9 | Cross-document | What do the papers say about chunk or passage size? | 7FP §3.1 and eRAG §3.1. Chunks from both files should appear in the top 5. | 3 (chunk from both files appear in top 5) | 0.373 | 0.329 | ✅ | - | outranked chunks are 6.1 Chunking and Embeddings chunk and FP3 Not in Context - Consolidation strategy Limitations respectively |
| Q10 | Equation | How does eRAG compute a relevance label for a document? | eRAG §2, Equation 1 and the text around it | 1 | 0.587 | 0.587 | ✅ | - | - |
| Q11 | Unanswerable, on-topic | Which vector database did the AI Tutor use? | Not stated anywhere. eRAG mentions a Faiss flat index, a plausible wrong chunk. | - | 0.528 | - | N/A | Corpus | 4.2 AI Tutor chunk at rank 1 | 
| Q12 | Unanswerable, off-topic | What is a good recipe for pancakes? | Nowhere. This gives you the floor score. | - | 0.191 | - | N/A | Corpus | - |

### Summary
- Hit@1 7/10; Hit@3 10/10; Hit@5 10/10 (9/10 fully answered at k=5); MRR 0.82. Q11/Q12 excluded (no answer exists; tested at answer level in M5).
- Score range: answerable top-1 0.340–0.697; Q11 0.528; Q12 0.191.
- Failures by cause: k 1 (Q3, second value at rank 8); extraction 0; chunking 0 (Q5/Q6 answers span two chunks, both retrieved); semantic 0.

### Observations
- All rank misses (Q2, Q4, Q9) were near-neighbor chunks from the correct paper, not unrelated chunks.
- Scores follow vocabulary: eRAG-specific questions >=0.53, 7FP-only questions <=0.41. Absolute scores are not comparable across questions, and a hit can score as low as 0.340 (Q8).
- Q11 (unanswerable, on-topic) scored 0.528 and rank 1 was the AI Tutor section: the embedding matched the entity, not the missing attribute. A similarity threshold cannot produce "not found"; M5's prompt has to.
- Q3: the paper contradicts itself (15,000 vs 4017 documents); at k=5 only 4017 was retrieved. A model would answer without noticing the conflict.
- Corpus is two documents and ten questions: a smoke test only.

### Hypotheses for EXP-001 onward
- Chunk size 300 vs 500 (after the eval set grows to ~30 questions)
- Prepend document title to the embedded text
- k=8 vs k=5 (Q3 would be a test case, once the cost in noise is measured)

## Answer level baseline

- Date: 27-10-2-26 
- Git commit: 0fea33a
- Chat model + temperature (default): ; PROMPT_VERSION: grounded-v1
- Retrieval: k=5 unless stated; voyage-4-lite; chunk 500/50
- Runs per question: 2–3 times, and outputs were stable

| Id | Ques | Answered | Correct | Citations valid | Citations support the claim | Notes | 
|---| ---|---|---|---|---|---|
| Q1 | On average, how many times faster is eRAG than end-to-end evaluation? | True | Yes | Yes | Yes | |
| Q2 | Which model was used as the default LLM in the eRAG experiments? | True | Yes | Yes | Yes | |
| Q3 | How many documents did the BioASQ experiment use? | True | Yes | Yes | Yes | K@5 does not includes 15,000 documents, K@8 has 15,000 in the retrieved chunk (15,000\ndocuments), but llm does not flags the conflict maybe because it does not reads the value from this chunk, possibly due to \n character between 15,000 and documents. K@10 retrieves a chunks with 15,000 documents and LLM does flags the conflict.|
| Q3 @k=5 | How many documents did the BioASQ experiment use? | True | Partial (4,017 only; conflict not flagged) | Yes | Yes | 15,000 chunk not retrieved (rank 8 in retrieval). FP2 in 7FP terms. |
| Q3 @k=8 | (same) | True | Partial (conflict not flagged) | Yes | Yes | answer in context, not extracted ("15,000\ndocuments"); model still answered 4,017 only. |
| Q3 @k=10 | (same) | True | Yes (conflict flagged) | Yes | Yes | Second chunk with "15,000 documents" retrieved; model flagged the conflict. |
| Q4 | What goes wrong when someone asks about a topic the knowledge base touches on but never actually answers? | True | Yes | Yes | Yes | |
| Q5 | Why not just have people label which passages are relevant when judging a retriever that feeds an LLM? | True | Yes | Yes | Yes | |
| Q6 | List all seven failure points. | True | Yes | Yes | Yes | Does list all the seven points.|
| Q7 | How much GPU memory did end-to-end evaluation need on NQ compared with eRAG? | True | Yes | Yes | Yes | Does correctly lists GPU memory from the table |
| Q8 | Which failure points does the lesson about continuous calibration relate to? | True | Yes | Yes | Yes | Does correctly fetchs the FP2-7 |
| Q9 | What do the papers say about chunk or passage size? | True | Yes | Yes | Yes | |
| Q10 | How does eRAG compute a relevance label for a document? | True | Yes | Yes | Yes | |
| Q11 | Which vector database did the AI Tutor use? | False | Correct refusal | - | - | LLM replies with "I could not find the answer in the provided documents." with No citations |
| Q12 | What is a good recipe for pancakes? | False | Correct refusal | - | - | LLM replies with "I could not find the answer in the provided documents." with No citations |
| Q13 | What GPU did the eRAG authors use, and what did training cost? | True | Yes | Yes | Yes | added after baseline-v0 (no retrieval row), Does correctly answers for GPU and specify absence of training cost in the documents. |

### Summary
- Answerable (Q1–Q10, Q13): 11/11 answered with valid citations that support the claims; 10 fully correct, 1 partial (Q3 at k=5 and k=8: only 4,017 reported, conflict not flagged).
- Unanswerable (Q11, Q12): 2/2 correct refusals (exact sentence, no citations), including Q11 where the AI Tutor chunk was rank 1.
- Partial-answer probe (Q13): gave the GPU and stated the training cost is not in the documents.
- Every retrieval ✅ led to a correct answer; no case of good retrieval followed by a wrong answer, except the Q3 conflict case (answer in context, not flagged).

### Observations
- Conflict flagging appeared only at k=10, when two chunks carried the 15,000 figure. Causes not isolated: number of mentions, position in context.
- The set is small and easy: 11/11 means it can't discriminate between pipeline variants. Expand to ~30 questions with harder cases before running EXP-001.

## EXP-001 — {Title}
- Date:
- Hypothesis:
- Change (one variable only):
- Dataset: (eval set version, # questions)
- Metrics before → after: recall@k / faithfulness / answer relevance
- Result:
- Decision: (keep / revert / follow-up, link ADR if any)