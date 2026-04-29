# CLAUDE.md — System-design teaching-repo starter

> A different shape from the code-grading template. The deliverable here is
> **a running service at a URL**, not a passing test suite on a fork. Each
> branch defines a system to design (cache, tinyurl, leaderboard, rate
> limiter). The learner picks any language/framework, hosts it, submits the
> URL — the LMS runs adversarial load tests against it.

---

## 0. North Star

A hands-on system-design course. Goal: teach learners to **design, build, and operate** a small distributed-systems primitive end-to-end — not to draw boxes on a whiteboard.

- `main` holds the API specs + load-test harnesses (read-only; learners don't fork-and-modify)
- Each `design/<slug>` branch is one system to build (cache / tinyurl / leaderboard / ratelimiter / pastebin / counter / chat)
- The learner builds the service in **any language/framework**, hosts it (Render/Fly/Railway/Heroku/local-with-tunnel), submits the URL
- The LMS runs hidden load + correctness tests against the URL and grades

**Why this shape:**
- Forces real choices: storage engine, cache eviction policy, idempotency keys, concurrency model
- Surfaces real failure modes: thundering herd, lost writes, race conditions, latency tails
- Language-agnostic on purpose: a learner who's strong in Go, weak in design will produce different bugs from one strong in Python — both are interesting

---

## 1. Project context

**This repo ships:**
- `design/<slug>` branches, each with a `SPEC.md` (API + SLOs) and a `grading/` directory of load-test scripts
- A shared `harness/` of tools the LMS-side grader uses (k6 scripts, correctness probes, telemetry parsers)
- Optional `starters/<lang>/<slug>/` skeletons in 2–3 languages

**This repo does NOT ship:**
- Reference implementations of the systems (gives away the design)
- Anything the learner imports, forks, or modifies. This is a spec/grader repo, not a starter repo.

**The learner's repo is THEIRS.** They build on their own GitHub (or wherever); this repo only provides the spec and the grader.

**Deployment options the learner can use** (declare which you support; affects URL submission):
- Public host: Render, Fly.io, Railway, Vercel, Heroku, fly hosted preview
- Cloudflare/AWS/GCP free tier
- Local + ngrok / Cloudflare Tunnel (good for cohort sessions; bad for async grading because the tunnel may be down when the grader runs)

---

## 2. Repo / branch layout

```
.
├── CLAUDE.md                         # this file
├── README.md                         # course map, syllabus, submission how-to
├── harness/                          # shared grader internals (LMS-only — see §6)
│   ├── load/                         # k6 scripts (or Locust, gatling — pick one)
│   ├── correctness/                  # adversarial Python probes
│   ├── slo.py                        # SLO assertion DSL (latency p95, error rate, throughput)
│   └── runner.py                     # entrypoint the LMS worker invokes
├── starters/                         # OPTIONAL — skeleton scaffolds the learner can copy
│   ├── go/cache/
│   ├── python/cache/
│   └── ts/cache/
└── design/<slug>/  (one branch per problem; on the branch:)
    ├── SPEC.md                       # API contract, SLOs, invariants — public
    ├── EXAMPLES.md                   # sample request/response pairs — public
    ├── grading/                      # PRIVATE in production (see §6)
    │   ├── load.k6.js                # load profile + thresholds
    │   ├── correctness.py            # adversarial sequences
    │   └── rubric.md                 # what the LLM judge scores beyond load+correctness
    └── EXERCISE.md                   # the prompt the learner reads
```

### Branch namespaces

| Prefix | Purpose | Has `SPEC.md`? | Has hidden grading? |
| --- | --- | --- | --- |
| `main` | reference (specs only, no implementations) | no | no |
| `design/<slug>` | one system to build | yes | yes (load + correctness + LLM rubric) |
| `tour/<slug>` | guided walkthrough of how grading works | no | no |
| `extra/<slug>` | playground or post-course extension | optional | optional |

`<slug>`: `cache | tinyurl | leaderboard | ratelimiter | pastebin | counter | chat | feed | search | queue`. Pick 4–6 for a v1 course.

---

## 3. The contract per system

Each `design/<slug>` branch ships these in `SPEC.md`:

### 3.1 API contract (the public part)

OpenAPI 3 fragment OR a `## API` section with:
- HTTP verbs + paths
- Request body schemas (JSON)
- Response schemas with status codes
- Error format
- Auth model (or "none for v1")

Example for `design/cache`:

```
PUT /v1/cache/{key}        body: {"value": str, "ttl_seconds": int?}     → 204
GET /v1/cache/{key}                                                       → 200 {"value": ...} | 404
DEL /v1/cache/{key}                                                       → 204 | 404
GET /v1/cache/_/stats                                                     → 200 {"size": int, "hits": int, "misses": int}
```

### 3.2 SLOs (the targets the grader enforces)

```yaml
# in SPEC.md
slos:
  read_p95_ms: 50
  write_p95_ms: 100
  error_rate_pct: 0.5
  sustained_rps: 200
  concurrent_clients: 50
```

The grader's `slo.py` reads these and asserts. Different systems get different defaults — a tinyurl needs higher RPS than a chat.

### 3.3 Correctness invariants

A bullet list of properties the system must hold. These become adversarial probes (§5).

For `design/cache`:
- After PUT k=v, GET k returns v (within consistency window if you choose eventual)
- After PUT k=v then DEL k, GET k returns 404
- TTL: after `ttl_seconds`, GET returns 404 (give a ±2s grace window)
- Concurrent PUTs to the same key: last-write-wins, no lost writes silently dropped
- `_/stats.size` matches the number of currently-live keys (counted independently by the probe)

For `design/tinyurl`:
- Same long URL → same short code (idempotent shortening)
- Two different long URLs → different short codes (no collisions across 1M codes)
- GET on a non-existent code → 404 (not a redirect to anywhere)
- Custom alias collisions → 409 Conflict, not silent overwrite

### 3.4 What the learner picks

- Storage engine (in-memory / Redis / Postgres / SQLite / DynamoDB)
- Eviction policy (LRU / LFU / TTL-only)
- Concurrency model (one process / N workers / cluster)
- Hosting

These choices are graded indirectly through the SLOs and the LLM rubric (§5).

---

## 4. Submission flow (how it differs from the code-grading model)

```
Learner: builds service on their own repo / their own host
         ↓
       deploys to a public URL  (e.g., https://cache-jane.fly.dev)
         ↓
       on the LMS: paste hosted_url + optional source_repo_url, click Submit
         ↓
LMS:   creates ExerciseSubmission(hosted_url=..., status='pending')
         ↓
       enqueues a LoadTestJob row in Postgres
         ↓
LMS worker:
  1. pre-flight: GET <hosted_url>/health — fail fast if unreachable
  2. correctness: run grading/<slug>/correctness.py against URL
  3. load:        run grading/<slug>/load.k6.js with the SLOs from SPEC.md
  4. (optional)   LLM judge reads source_repo_url + load metrics, scores rubric
  5. write back:  status='completed', score, slo_violations, latencies, judge_feedback
         ↓
Learner sees grade + per-axis breakdown on the slide.
Admin sees aggregate cohort progress.
```

**No GitHub Actions involvement.** The grader runs entirely on LMS infrastructure. (See §7 — this affects the GitHub-free-minutes question.)

---

## 5. The grading harness — what runs against the URL

Three layers, ordered cheap-to-expensive:

### 5.1 Pre-flight probe

A 5-second sanity check before spending compute on load:
- Service reachable (`GET /health`, 200)
- API smoke: one happy-path PUT + GET round-trip
- Schema check: response body matches SPEC

If pre-flight fails, the rest is skipped and the submission is marked `unreachable`. This protects the LMS from spending 10 minutes load-testing a 502.

### 5.2 Correctness probe (adversarial sequences)

A Python script per system that issues sequences of requests designed to violate invariants. Each invariant from §3.3 becomes one or more probe sequences:

```python
# grading/cache/correctness.py — sketch
async def test_ttl_expiry(client):
    r = await client.put("/v1/cache/k", json={"value": "v", "ttl_seconds": 2})
    assert r.status == 204
    r = await client.get("/v1/cache/k"); assert r.status == 200
    await asyncio.sleep(2.5)
    r = await client.get("/v1/cache/k"); assert r.status == 404, "TTL not honoured"

async def test_concurrent_puts_same_key(client):
    # 200 concurrent PUTs to the same key; assert exactly one wins; no 5xx
    ...
```

Each probe is one assertion. The output is a structured pass/fail per invariant.

### 5.3 Load profile (SLO enforcement)

A k6 (or Locust) script per system that ramps to the SLO traffic:

```javascript
// grading/cache/load.k6.js — sketch
export const options = {
  stages: [
    { duration: '30s', target: 50 },     // warm-up
    { duration: '1m',  target: 200 },    // sustained
    { duration: '15s', target: 0  },     // cool-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<50'],     // matches SPEC.slos.read_p95_ms
    http_req_failed:   ['rate<0.005'],   // matches SPEC.slos.error_rate_pct
  },
};
```

Output: a JSON metrics file the LMS parses into `grading-result.json` shape (extended with `latencies`, `rps`, `slo_violations`).

### 5.4 (Optional) LLM judge over source

If the learner provided `source_repo_url`, an LLM judge clones it, reads the implementation, and scores against `grading/<slug>/rubric.md`:
- Choice of storage / eviction policy: explained in a README?
- Concurrency primitives used correctly?
- Tests in the learner's own repo?
- Observability (logs, metrics) wired up?

Bonus axis only — not a gate.

---

## 6. Why `grading/` must be private (and how)

For code-grading repos, "hidden" tests live in the public repo under `grading/` — they're hidden from the learner's *visible test path* but visible if they look. Good enough for honour-system courses.

**For system-design repos, `grading/` should be genuinely private.** Two reasons:

1. **The probes encode the failure modes.** A learner reading `correctness.py` sees exactly which sequences will be tested — a much bigger spoiler than "this branch is about validation".
2. **Adversarial load profiles are tunable.** If a learner sees `target: 200`, they tune for 200 RPS. We want them to design for the *spec*, not the test.

Two ways to achieve this:

| Approach | How | Trade-off |
| --- | --- | --- |
| **Two-repo split** | Public `<repo>` has SPECs + EXERCISE.md; private `<repo>-grading` has the harness. LMS pulls from both. | Cleanest separation; needs LMS access to the private repo |
| **Single repo, grading branch on private fork** | Public repo for SPECs; the LMS clones a private fork that has `grading/<slug>/` populated. | Easier ops if you already have a single-repo flow |

Pick one and document it in `harness/README.md`. The reference implementation should never reveal the load profile or the adversarial probe contents.

---

## 7. GitHub Actions implications (and the free-minutes question)

### Free GitHub Actions allowance per learner (public repos)

| Plan | Public repo minutes | Private repo minutes |
| --- | --- | --- |
| **Free** | unlimited | 2,000 / month |
| **Pro** | unlimited | 3,000 / month |
| **Team** | unlimited | 3,000 / month |
| **Enterprise** | unlimited | 50,000 / month |

For a code-grading teaching repo (the canonical template), this matters: each push triggers a CI run on the learner's fork. A 2-minute test × 50 pushes = 100 minutes of their quota. Realistic across a 14-week cohort: ~500–1000 minutes per learner. Fine on free for public repos, fine on private for any plan.

For a **system-design teaching repo** (this template), GitHub Actions free minutes barely matter:
- The teaching repo's CI doesn't grade — grading is on LMS infrastructure
- The learner may use Actions on *their own* implementation repo (running their own tests, deploying to Render/Fly), but that's their choice and not driven by our course
- The LMS load-test workers are the bottleneck, not GitHub

So the free-minutes answer for **this** template: **GitHub Actions free minutes are essentially unlimited** for the learner because the grading isn't gated on Actions. Plan capacity for the **LMS load-test workers** instead — that's where the real cost lives.

---

## 8. Backend changes from the code-grading LMS

If you're extending the canonical `claude-code-lms` to support this template, here are the additions:

### 8.1 Schema additions

```sql
ALTER TABLE modules ADD COLUMN module_type TEXT DEFAULT 'code'
    CHECK (module_type IN ('code', 'system-design'));

-- Per-submission for system-design modules:
ALTER TABLE exercise_submissions
    ADD COLUMN hosted_url      TEXT,
    ADD COLUMN source_repo_url TEXT,
    ADD COLUMN preflight_ok    BOOLEAN,
    ADD COLUMN correctness_pass INT,    -- of N probes
    ADD COLUMN correctness_total INT,
    ADD COLUMN p50_ms FLOAT, ADD COLUMN p95_ms FLOAT, ADD COLUMN p99_ms FLOAT,
    ADD COLUMN error_rate_pct FLOAT,
    ADD COLUMN sustained_rps FLOAT,
    ADD COLUMN slo_violations JSONB,
    ADD COLUMN judge_score INT,
    ADD COLUMN judge_feedback JSONB;

-- New job kind:
CREATE TABLE load_test_jobs (
    id BIGSERIAL PRIMARY KEY,
    submission_id BIGINT REFERENCES exercise_submissions(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP, finished_at TIMESTAMP, heartbeat_at TIMESTAMP,
    last_error TEXT, attempts INT DEFAULT 0
);
```

### 8.2 New worker: `loadtest_worker`

Same `FOR UPDATE SKIP LOCKED` pattern as the existing `worker/`, but drains `load_test_jobs` instead of `generation_jobs`. For each job:

```python
async def run_load_job(session, job):
    sub = await session.get(ExerciseSubmission, job.submission_id)
    module = await session.get(Module, sub.module_id)
    slug = module.branch_name.replace('design/', '')

    # 1. preflight
    if not await preflight(sub.hosted_url):
        sub.preflight_ok = False; sub.status = 'unreachable'; return

    # 2. correctness — runs from harness/correctness.py + grading/<slug>/correctness.py
    cr = await run_correctness(sub.hosted_url, slug)
    sub.correctness_pass, sub.correctness_total = cr.passed, cr.total

    # 3. load — invoke k6 binary, parse JSON output
    lr = await run_k6(sub.hosted_url, slug)
    sub.p50_ms, sub.p95_ms, sub.p99_ms = lr.p50, lr.p95, lr.p99
    sub.error_rate_pct, sub.sustained_rps = lr.err_pct, lr.rps
    sub.slo_violations = lr.violations

    # 4. (optional) judge
    if sub.source_repo_url:
        jr = await run_judge(sub.source_repo_url, slug)
        sub.judge_score, sub.judge_feedback = jr.total, jr.feedback

    sub.status = 'completed'
```

### 8.3 New routes

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/courses/{slug}/modules/{branch_slug:path}/system-design-submit` | Accepts `{hosted_url, source_repo_url}` instead of fork-URL fields. Inserts both `ExerciseSubmission` and `LoadTestJob`. |
| `GET` | `/admin/load-jobs` | Per-job status; useful for debugging stuck loadtests. |

The existing `/webhooks/github` becomes irrelevant for system-design modules — there's no GitHub Actions to listen for.

### 8.4 Slide-3 template change

For `module.module_type == 'system-design'`, the form has two fields (`hosted_url`, `source_repo_url`) and a status panel that shows the four metric blocks (preflight / correctness / latency / SLO conformance). For code modules, the existing fork-URL form stays.

### 8.5 Operational concerns

- **Load runner sandboxing**: don't run k6 in-process on the LMS web. Separate worker process or container. Resource caps (CPU, time).
- **Outbound rate limiting per learner**: a learner accidentally submitting a URL that's also their AWS metadata endpoint shouldn't blow up their account. Validate URL scheme + host.
- **Test parallelism**: cap concurrent load tests system-wide (k6 is heavy). 2–4 in-flight is sane on a single VM.
- **Cost**: 1 minute of k6 at 200 RPS = ~12k requests. The LMS bears the bandwidth + compute. Budget: ~$0.05/grading run on cheap cloud.

---

## 9. Authoring loop for a system-design exercise

1. Branch from `main`: `git checkout -b design/<slug> main`
2. Write `SPEC.md`: API contract, SLOs, correctness invariants
3. Write `EXAMPLES.md`: 5–10 sample request/response pairs
4. Write `grading/<slug>/correctness.py`: one probe per invariant in §3.3
5. Write `grading/<slug>/load.k6.js`: load profile matching SLOs
6. Write `grading/<slug>/rubric.md` (optional): LLM-judge axes for source-code review
7. Build a reference implementation **in a private gist or repo** (not committed here). Run the harness against it: confirm correctness probes pass, SLOs achievable.
8. Write `EXERCISE.md`: framing of the problem (story / use case / scale numbers), point at SPEC, no spoilers.
9. Verify: pretend to be a learner, submit a deliberately-broken URL, confirm grader produces actionable feedback.
10. Update README map.

---

## 10. EXERCISE.md template (per design branch)

```markdown
# Design: <System name>

**Type:** system-design — build, host, submit a URL.
**Estimated time:** <several hours to a day, depending on scope>

## The problem

<2-paragraph framing. The use case, not the API. "You're building Y because of Z.">

## What you're building

<1-paragraph summary. Point at SPEC.md for the contract.>

→ See [`SPEC.md`](SPEC.md) for the API + SLOs.
→ See [`EXAMPLES.md`](EXAMPLES.md) for sample requests/responses.

## Constraints

- Any language, any framework
- Must be reachable on a public URL when you submit
- Must implement the SPEC's API verbatim (paths, status codes, body shapes)
- Pick your own storage / concurrency model — both are graded indirectly via SLOs

## How you're graded

| Axis | Weight | What it measures |
| --- | --- | --- |
| Pre-flight | gate | service reachable + smoke test passes |
| Correctness | 50% | invariants hold under adversarial sequences |
| Load / SLO | 30% | p95 latency, error rate, sustained RPS at the SPEC's targets |
| Source-code review (optional) | 20% bonus | LLM judge reviews your repo if you submit one |

The full grader runs against your URL when you submit. Plan for ~3 minutes of grading time per submission.

## Hosting suggestions

- Render / Fly.io / Railway free tier — 30s cold start
- Cloudflare Workers / Vercel — sub-100ms cold start, harder for stateful systems
- Local + ngrok or Cloudflare Tunnel — fine for live sessions, fragile for async grading

## See also

[`SPEC.md`](SPEC.md), [`EXAMPLES.md`](EXAMPLES.md), [`AGENT_INSTRUCTIONS.md`](AGENT_INSTRUCTIONS.md).
```

---

## 11. Anti-gaming for system-design

The threat model differs from code-grading:

- **Spec-leak via probe inspection** — addressed by §6 (private grading)
- **Pre-warming** — the learner deploys a beefier instance just before grading. Mitigation: sustained-load over 1–2 minutes (not a 5-second burst); instance scaling is a feature, not gaming.
- **Ghost endpoints** — the URL serves cached / canned responses for the API paths the learner saw in EXAMPLES.md but fails on novel ones. Mitigation: correctness probe issues sequences with fresh, unguessable keys.
- **Per-learner spec variants** — same as code-grading: vary the load profile slightly per `(course, branch, user)` so cohort-wide replay attacks fail.

---

## 12. v1 readiness checklist

- [ ] `main` has the `harness/` skeleton + `README.md` syllabus
- [ ] At least 3 `design/<slug>` branches, each with SPEC.md, EXAMPLES.md, grading scripts
- [ ] Reference implementation exists privately for each — confirm grading is achievable in 4–6 hours of effort
- [ ] LMS has the schema + worker + route changes (§8)
- [ ] One end-to-end smoke: submit a deliberately-buggy URL, see correctness probes fail; submit a correct one, see SLOs satisfied
- [ ] Cost dashboard: per-submission grading cost is bounded
- [ ] Private grading separation (§6) is in place — the public repo doesn't reveal probe contents
- [ ] Hosted URL validation: reject internal-network URLs, AWS/GCP metadata endpoints, etc.

---

## §A. Recommended starter problems

| `<slug>` | Time budget | Teaches |
| --- | --- | --- |
| `cache` | 6h | TTL, eviction policy, concurrent writes, hit-rate observability |
| `tinyurl` | 4h | hash-vs-counter ID generation, idempotency, 1M-entry collision avoidance, custom-alias conflicts |
| `ratelimiter` | 8h | token bucket vs leaky bucket vs fixed window, distributed counter, burst handling |
| `leaderboard` | 6h | sorted-set ops, top-N queries, ties, score updates under contention |
| `pastebin` | 4h | content-addressed storage, expiry, size limits |
| `chat` | 12h | WebSocket / SSE, fan-out, message ordering, online-presence eventually-consistent |
| `feed` | 12h | push vs pull, fan-out-on-write vs fan-out-on-read, hot-key handling |
| `counter` | 4h | distributed counter, near-real-time vs exactly-correct, eventual consistency demos |

Pick 4–6 in your v1, in roughly increasing complexity.

---

## §B. Reference: how the code-grading template differs

| | Code-grading template | System-design template (this) |
| --- | --- | --- |
| Branch contains | code + visible tests | spec + adversarial probes |
| Learner ships | passing tests on their fork | running service at a URL |
| Grader runs on | learner's GitHub Actions | LMS infrastructure |
| Submission stores | fork URL + branch | hosted URL (+ optional source repo) |
| Webhook flow | yes, `workflow_run` from GitHub | no, polled by LMS load-test worker |
| Free GH Actions minutes | matters (~500/learner across cohort) | doesn't matter |
| Per-submission cost | ~$0 (runs on GitHub) | ~$0.01–0.10 (LMS k6 + judge tokens) |

Both templates live alongside in `claude-code-lms/templates/`. The same LMS runs both; modules just have a `module_type` flag (§8.1).
