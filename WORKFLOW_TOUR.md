# How this course works — workflow tour

15-minute walkthrough. By the end you'll have submitted a (deliberately broken) URL to feel the grading flow before tackling design/01.

## What's different from a code-grading course

| | Code-grading | This course (system-design) |
| --- | --- | --- |
| Branch contains | code + tests | spec + adversarial probe set |
| You ship | a passing test suite on your fork | a service running at a public URL |
| Grader runs on | your GitHub Actions | the LMS infrastructure |
| Submission is | a fork URL + branch name | a hosted URL |
| What's graded | did `mvn test` pass | did the LMS judge probe your URL and like the answers |

You won't fork. You'll build any service in any language and host it anywhere reachable. The deliverable is the URL.

## The five-step loop

```
1. checkout the design/<n> branch
2. read SPEC.md + EXAMPLES.md
3. build a service that satisfies the spec (any stack)
4. host it (Render / Fly / Railway / your own VPS)
5. submit the URL on the LMS — the judge probes and scores it
```

## Stop 1 — the LMS lives at <LMS_HOST>

Sign up. Pick the **AI System Design — RAG + LangChain** course on the home page. Click into the first module (`tour/workflow` — that's this one).

## Stop 2 — let's submit a deliberately-broken URL

For this tour, submit a URL that doesn't actually serve anything. Use any of:

```
https://example.com
http://httpbin.org/status/404
http://your-non-existent.invalid
```

The pre-flight (`GET /health`) will fail. You'll see:

```
status:    unreachable
critique:  pre-flight failed: GET https://example.com/health returned 404 (or "no route to host")
```

That's the **pre-flight gate** in action. Before any judge tokens get spent, the LMS checks that your URL actually responds. Saves the budget for real submissions.

## Stop 3 — what a successful submission looks like

When your real service is up, the LMS runs:

1. **Pre-flight**: `GET /health` → 200
2. **Test probes**: each test in the branch's `judge.json` runs against your URL
3. **LLM judge**: claude-sonnet-4-5 reads each test's input + your service's response + the rubric, and assigns a 0–10 score per test
4. **Aggregate**: weighted percent across all tests
5. **Critique**: a paragraph per test naming what was good and what was off, citing the actual response body

Pass: ≥60%. The LMS shows your score, the per-test breakdown, and the critique.

## Stop 4 — the rubric is public

Each branch's `grading/<slug>/rubric.md` is in the repo, in plain sight. Read it before you start coding. It's the spec — the judge follows it strictly.

> Why is the rubric public? In a system-design course, the rubric IS the spec. Hiding it produces worse outcomes — learners over-engineer in the wrong direction. The probe set in `judge.json` is also public for now (it'll move to private grading in v2). Building to the test is fine in this course because the test IS the contract.

## Stop 5 — what to do after this tour

```bash
git checkout design/01-semantic-search
cat EXERCISE.md
```

Build, host, submit. Read the critique. Fix. Re-submit. Move on when ≥60%.

## What to watch for

- **Pre-flight failures** are the #1 first-submission issue. Most often: cold-start on Render/Fly takes >30s and the judge gives up.
- **Schema failures** are #2. The SPEC says `citations: array<string>`; if you return `citations: null` because there were no citations, you fail the schema test. Use `[]`.
- **Faithfulness failures** show up on design/02 onwards. You'll see the judge quote the unsupported claim back at you in the critique.

That's the whole tour. Total time so far: 15 minutes. Onward.
