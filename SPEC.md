# SPEC — design/02-rag-qa

A RAG service that retrieves relevant documents from the corpus AND generates a grounded answer with citations.

## Endpoints

### `POST /ask`

```http
POST /ask HTTP/1.1
Content-Type: application/json

{ "question": "What is BM25 and what makes it different from vector search?" }
```

→ `200 OK`

```json
{
  "question": "What is BM25 and what makes it different from vector search?",
  "answer": "BM25 is a bag-of-words ranking function that uses term frequency and inverse document frequency. Unlike vector search, BM25 requires exact term matches — so 'database' and 'databases' are different unless stemmed. BM25 wins on keyword-heavy queries, named entities, and rare terms.",
  "citations": ["d003"],
  "retrieved_doc_ids": ["d003", "d004", "d011"]
}
```

When the question is **out of corpus** or the retrieval is too weak to answer:

```json
{
  "question": "What's the airspeed velocity of an unladen swallow?",
  "answer": "I don't have information about that in my knowledge base.",
  "citations": [],
  "retrieved_doc_ids": ["d011", "d005", "d014"]
}
```

### `GET /health` → `200 {"ok": true}`

## SLOs

```yaml
read_p95_ms: 5000          # /ask end-to-end (retrieval + LLM call)
error_rate_pct: 1.0
sustained_rps: 5
```

## Correctness invariants

The judge verifies:

1. **Faithfulness** — `answer` text only contains facts present in `retrieved_doc_ids`. The LLM must not hallucinate. The judge re-reads the retrieved docs and rates whether each claim in the answer is supported.
2. **Citation accuracy** — every `doc_id` in `citations` is also in `retrieved_doc_ids` AND the cited doc actually contains material relevant to the answer.
3. **Refusal on OOC** — for questions whose answer isn't in the corpus, `citations` MUST be empty and `answer` MUST express uncertainty (e.g., "I don't know", "not in my knowledge base", "I can't answer that from the available documents").
4. **Refusal isn't lazy** — the service must NOT refuse to answer questions the corpus DOES support. The judge probes both.
5. **Citations subset retrieved** — `citations ⊆ retrieved_doc_ids`. Always.
6. **Schema strictness** — `citations` is `[string]`, never `null`. `retrieved_doc_ids` is `[string]` of length ≥ 1 (you always retrieve *something*, even on OOC questions).

## Constraints

- **Corpus**: same `corpus/docs.json` from `main` (15 documents).
- **Retriever**: any. Reuse design/01's if you have one.
- **Generator**: any LLM you control — OpenAI, Anthropic, Cohere, a local model, even a small Llama. The judge tests the *output behavior*, not the model identity.
- **Hosting**: any public URL.

## What you're being graded on (rubric.md preview)

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight + SLO | gate | `/health` 200, `/ask` p95 < 5000ms |
| Schema | 15% | fields present, types right, citations ⊆ retrieved |
| Faithfulness (in-corpus) | 35% | every claim in `answer` is supported by a retrieved doc |
| Citation accuracy | 20% | cited docs are *actually* relevant to the answer |
| OOC refusal | 20% | OOC questions get empty citations + uncertainty expression |
| Non-lazy answer | 10% | in-corpus questions get real answers, not blanket refusals |

## Examples

See [`EXAMPLES.md`](EXAMPLES.md).

## Authoring tip

The two failure modes to design against:

1. **Hallucination**: the LLM generates a plausible answer that's NOT in the retrieved docs. Mitigate by passing the docs as context with a strict system prompt: *"Answer only from the documents below. If they don't support an answer, say 'I don't know'."*
2. **Lazy refusal**: the LLM defaults to "I don't know" for any tricky question, even when the docs support an answer. Mitigate by including in your prompt: *"If the documents support an answer, give it. Don't refuse out of caution."*

Both failure modes are graded.
