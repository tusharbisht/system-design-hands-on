# Rubric — design/02-rag-qa

The judge runs the tests in `judge.json` and asks an LLM to score each one 0–10 against this rubric.

## Test types

### `smoke`

Shape correctness — fields present, types correct, status 200, `citations ⊆ retrieved_doc_ids`. Score 10 on full match; 0 on schema violation; partial credit for missing fields (-2 each).

### `qa` (in-corpus)

A question whose answer IS in the corpus. Score on TWO things:

**(a) Faithfulness** — does the `answer` actually use information from the cited docs? Re-read the cited docs. If a claim in the answer isn't supported, dock heavily.

**(b) Citation accuracy** — every cited doc should be relevant. Citing extra unrelated docs is a deduction.

| Outcome | Score |
| --- | --- |
| Answer is correct, all claims supported, citations are relevant + minimal | **10** |
| Answer is correct, citations include 1 unrelated doc | 8 |
| Answer is correct but cites unrelated docs heavily | 5 |
| Answer mostly correct but contains 1 unsupported claim | 4 |
| Answer is correct but `citations` is empty (didn't bother) | 3 |
| Answer is wrong / hallucinated | **0** |

The `expected.answer_must_mention` field gives a string the answer should contain (substring match, case-insensitive). Use it as a quick correctness check; don't dock just for *paraphrasing*.

### `refusal` (out-of-corpus or near-corpus-not-answerable)

A question whose answer is NOT in the corpus. The service must:
1. Express uncertainty in `answer` (e.g., "I don't know", "not in my knowledge base", "I can't answer this from the available documents").
2. Return `citations: []`.

| Outcome | Score |
| --- | --- |
| Clean refusal: empty citations, answer expresses uncertainty | **10** |
| Empty citations but answer is wishy-washy (still hints at an answer) | 6 |
| Provides an answer but with empty citations (worse — looks like hallucination) | 3 |
| Provides answer + citations as if confident | **0** |

For `near-corpus-01` (Tagalog chunking): `must_not_invent_specifics: true` means dock 5 points if the answer cites a specific number or recommendation that isn't in the corpus, even if it added "but I'm not sure".

### `qa` with `must_not_refuse: true` (non-lazy)

A question that IS answerable. If the service refuses, score 0. The lazy refusal penalty.

| Outcome | Score |
| --- | --- |
| Real answer with relevant citations | **10** |
| Real answer with no citations | 5 |
| Lazy refusal | **0** |

### `latency`

p95 across all `/ask` calls in the suite. SLO is 5000ms.

| Outcome | Score |
| --- | --- |
| p95 < 2000ms | **10** |
| p95 2000–5000ms | 8 |
| p95 5000–8000ms | 5 |
| p95 > 8000ms or > 10% timeouts | **0** |

## Pre-flight gate

`GET /health` 200 within 10s. If not: total score 0, critique = "service unreachable".

## Overall scoring

Weighted percent. Pass: ≥60%.

## Strictness note

When scoring qa/refusal:
- Quote the exact `observed.body.answer` string (or its first 100 chars) in your reasoning
- Quote the exact `observed.body.citations` array in your reasoning
- If you're docking on hallucination, name the exact unsupported claim

Generic critiques like "answer was OK" are docked 1 point on overall_critique quality.
