# Solving Design 02 with Claude Code — faster and better

The judge here is harsher than design/01: it doesn't just check whether you retrieved the right docs, it reads your answer and looks for hallucination. Spend the time on prompt engineering and probe-yourself-before-submit; the deploy is the easy part.

## Recommended workflow

### 1. Reuse design/01's retriever — don't rebuild

> "I have a working semantic search service from design/01 deployed at <URL>. Set up `/ask` as a wrapper that calls my own `/search` to retrieve top-3, then calls Claude/OpenAI to answer. No need for a second vector store."

Cuts your day in half. The two services don't even need to be the same process — `/ask` can be a thin wrapper.

### 2. Write the prompt by hand, then ask Claude to harden it

> "Here's my draft system prompt for the `/ask` endpoint: [...]. Critique it on three axes: (a) does it prevent hallucination, (b) does it prevent lazy refusal, (c) is the citation format machine-parseable. Suggest 3 specific improvements with one-line each, no rewrites."

This is the highest-ROI move on this branch. Most prompt engineering wins are 5-line edits to the system prompt; full rewrites are rarely better.

### 3. Probe yourself with the four-quadrant test set

Before submitting:

```python
# probe.py
in_corpus = [
    "What does VACUUM do?",
    "How do I rate-limit API requests?",
    "What chunk size for RAG?",
]
near_corpus_no_answer = [
    "What chunk size for embeddings trained on Tagalog?",
    "How does BM25 perform on Mandarin queries?",
]
out_of_corpus = [
    "Population of Tokyo?",
    "Best programming language for embedded?",
]
multi_doc = [
    "How does hybrid search combine BM25 and embeddings?",
    "What's the relationship between cosine similarity and dot product for normalized vectors?",
]

for q in in_corpus + near_corpus_no_answer + out_of_corpus + multi_doc:
    r = httpx.post(URL + "/ask", json={"question": q}).json()
    print(f"Q: {q}")
    print(f"  answer: {r['answer'][:120]}")
    print(f"  citations: {r['citations']}")
```

Run it, eyeball the four columns:

| Column | Should look like |
| --- | --- |
| `in_corpus` | concrete answer, citations non-empty |
| `near_corpus_no_answer` | refusal, citations empty (THIS is where you'll fail first) |
| `out_of_corpus` | refusal, citations empty |
| `multi_doc` | answer references multiple docs, citations contains 2+ ids |

If `near_corpus_no_answer` returns a confident-sounding answer with citations, your hallucination guard is too weak.

### 4. The "cite-then-answer" trick

A common pattern that works:

```
System prompt:
"Given the documents below, first identify which (if any) support the
question, by listing their IDs. Then answer ONLY using those IDs. If
none support the question, say 'I don't know' and cite nothing."

Documents:
[d001] ...
[d003] ...
[d005] ...

Question: <user question>

Format your reply as:
SUPPORTS: [d001, d003]
ANSWER: ...
CITATIONS: [d001, d003]
```

Then parse SUPPORTS/ANSWER/CITATIONS markers (regex is fine for fixed markers — see Hint 3 in EXERCISE.md). This forces the model to commit to docs *before* generating, which reduces post-hoc justification ("the doc supports my answer because it kind of mentions...").

### 5. Test the determinism — the judge runs the same question twice

Same question, different answer = your service has temperature > 0 or seed isn't pinned. Set `temperature: 0` (or very low) for the QA endpoint. It's not graded explicitly but flaky answers will sometimes fail the recall checks.

### 6. Submit, read the critique, iterate

Don't fix everything in your local probe before the first submit. The first submit is *information-gathering*. Read the judge's per-test critique:

> "score 4: cited d011 (LangChain at a glance) but the question was about BM25 (d003). The retrieval surfaced d003 in retrieved_doc_ids but the answer text uses LangChain terminology."

That tells you exactly what's wrong: your retrieval is fine but the LLM is being misled by an irrelevant doc in context. Either tighten the top-K cutoff or improve the prompt to say *"focus on the most relevant doc, ignore others if they don't apply"*.

## Claude Code techniques that pay off here

| Technique | Why it matters here |
| --- | --- |
| **Reuse design/01's `/search`** | building two retrievers wastes a day |
| **Prompt critique → 3 line edits** | better than full rewrites; preserves what works |
| **Four-quadrant probe** | distinguishes the four failure modes — in-corpus vs near vs OOC vs multi-doc |
| **Cite-then-answer pattern** | forces commitment to docs before generation |
| **Read the judge's per-test critique** | the wording tells you EXACTLY which axis you missed |

## What NOT to do

- **Don't use `temperature > 0.2`.** Determinism + strictness > fluency on this branch.
- **Don't put the full corpus in every prompt.** Only the retrieved top-3. Otherwise you're not really doing RAG.
- **Don't return retrieved_doc_ids = []**. Even on OOC questions, retrieval *runs* and returns something. The judge expects at least 1 entry.
- **Don't try to parse free-form citations from the LLM body.** Use structured markers (cite-then-answer) or your provider's native structured-output feature.
- **Don't include corpus content in your hosted service's source repo.** Pull it from `main` of this repo at startup. That way if the corpus changes, you re-ingest cleanly.

## When you're stuck

> "The judge says my answer for 'what is BM25' is hallucinating because I cited d011 (LangChain) instead of d003 (BM25 explained). Both docs were in retrieved_doc_ids. Walk me through my prompt — why is the model picking the wrong doc to cite even when the right one is there?"

(Common cause: the system prompt says "use any doc that's relevant" without ranking. Fix: instruct the model to use the highest-relevance doc primarily, and to ignore lower-ranked docs unless directly needed.)
