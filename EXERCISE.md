# Design 02 — RAG QA

**Type:** system-design — build, host, submit a URL
**Estimated time:** 6–8h with Claude Code
**Auto-graded:** answer faithfulness, citation accuracy, OOC refusal, non-lazy answers

## The problem

A retrieval system that *finds* documents (design/01) is half a useful system. Now: take the user's question, find the relevant docs, and synthesise a grounded answer using an LLM. The hard part isn't generating fluent text — it's preventing the LLM from making up facts the docs don't support.

## What you're building

`POST /ask` takes a question and returns:
- `answer` — natural-language response
- `citations` — list of `doc_id` the answer is grounded in (subset of retrieved)
- `retrieved_doc_ids` — what the retriever returned (full list, before generation)

Plus `GET /health`. Full contract in [`SPEC.md`](SPEC.md), examples in [`EXAMPLES.md`](EXAMPLES.md).

## What "done" looks like

The judge probes 8–10 questions covering:
- Directly answerable single-doc questions
- Multi-doc synthesis questions
- OOC questions (corpus has nothing; you must refuse)
- Adversarial near-corpus questions (looks answerable but isn't; you must NOT invent)
- Plain in-corpus questions (you must NOT lazy-refuse)

Pass: ≥60% weighted score. Strong pass: ≥80% with low hallucination rate.

## Two failure modes you're being graded on

### 1. Hallucination

LLM generates a plausible answer that the retrieved docs DON'T support. The judge re-reads your retrieved docs and explicitly checks each claim in your answer is grounded.

**Mitigate**: a strict system prompt — `"Answer ONLY from the documents below. If they don't support an answer, say 'I don't know'. Don't add general knowledge."`

### 2. Lazy refusal

LLM defaults to "I don't know" for any tricky question, even when the corpus supports an answer. Conservative-looking, but useless.

**Mitigate**: add to the prompt — `"If the documents support an answer, give it. Don't refuse out of an excess of caution."`

You're balancing these two — too aggressive on prompt 1 → lazy refuser. Too aggressive on prompt 2 → hallucinator. The sweet spot is what the judge rewards.

## Constraints

- Reuse design/01's retriever (or build a fresh one — your call)
- Any LLM (OpenAI, Anthropic, Llama, Mistral, anything)
- The corpus is the same 15-doc `docs.json` from `main`
- Don't pre-bake answers — the judge will probe variations

## Hints

<details><summary>Hint 1 — top-K is your knob, not a constant</summary>

Retrieve top 3–5 docs as context. Too few and you'll miss multi-doc synthesis. Too many and the LLM gets distracted (and you blow the latency SLO). 3 is the right starting point for this corpus size.

</details>

<details><summary>Hint 2 — the model needs to know which docs to cite</summary>

Format your prompt so the LLM sees doc IDs:

```
Document d001: Postgres uses Multi-Version Concurrency Control...
Document d003: BM25 is a bag-of-words ranking function...
...

Question: What does VACUUM do in Postgres?

Answer the question using ONLY the documents above. List the doc IDs you used in a `citations` field.
```

If the model can't see the IDs, it can't cite them. Most cited-RAG implementations make this exact format mistake the first time.

</details>

<details><summary>Hint 3 — extract the citation list deterministically</summary>

Don't ask the LLM to format citations as JSON inline — it'll hallucinate the JSON shape on edge cases. Instead: ask for `[citations: dN, dM]` markers, then extract them with a regex *after* the LLM call. Or use structured outputs (OpenAI / Anthropic tool-use). The latter is more reliable.

(Yes — this is a regex on LLM output. It's the legitimate exception in our anti-regex rule: parsing structured markers at a layer boundary, not "scrubbing bad output".)

</details>

<details><summary>Hint 4 — refusal needs an explicit signal in the prompt</summary>

Add to your prompt: `"If the documents do NOT support an answer to the question, respond with exactly 'I don't know' or 'Not in my knowledge base' and leave citations empty."`

Test this with the OOC examples in EXAMPLES.md. If your model still tries to bluff, lower the temperature or add a few few-shot examples of correct refusal.

</details>

## See also

- [SPEC.md](SPEC.md), [EXAMPLES.md](EXAMPLES.md)
- [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md)
- [grading/design-02-rag-qa/](grading/design-02-rag-qa/)
