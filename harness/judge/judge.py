"""LLM-judge harness for design/* branches.

Reads a `judge.json` test set + a `rubric.md`, hits the learner's hosted URL
with each test, asks an LLM to score the response. Writes JSON.

Used by:
  - the LMS server-side worker (real grading)
  - the learner locally (`python harness/judge/judge.py --url ... --branch ...`)

Schema for a judge.json:
{
  "branch": "design/01-semantic-search",
  "endpoint": "POST /search",
  "tests": [
    {
      "id": "t01",
      "type": "ranking" | "qa" | "refusal" | "smoke" | "latency",
      "input": { ... arbitrary JSON sent as the request body ... },
      "expected": { ... criteria the rubric checks ... },
      "weight": 1.0
    }
  ]
}

Schema for rubric.md: free-form markdown — passed to the LLM judge as the
instruction prompt. Should describe what each `type` field means and how
strictly to score.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

try:
    import httpx
    import anthropic  # type: ignore[import-not-found]
except ImportError:
    sys.stderr.write("install deps: pip install httpx anthropic\n")
    sys.exit(2)


JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-5")
JUDGE_TIMEOUT_SEC = int(os.environ.get("JUDGE_TIMEOUT_SEC", "30"))


async def make_request(client: httpx.AsyncClient, base: str, endpoint: str, body: dict[str, Any] | None) -> dict[str, Any]:
    """Hit `<base><path>` with `<method>` and capture status, body, latency."""
    method, _, path = endpoint.partition(" ")
    method = method or "GET"
    url = base.rstrip("/") + path
    t0 = time.monotonic()
    try:
        if method.upper() == "GET":
            r = await client.get(url, timeout=JUDGE_TIMEOUT_SEC)
        else:
            r = await client.request(method.upper(), url, json=body, timeout=JUDGE_TIMEOUT_SEC)
    except httpx.HTTPError as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "latency_ms": int((time.monotonic() - t0) * 1000)}
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    try:
        parsed = r.json()
    except ValueError:
        parsed = r.text[:500]
    return {"status": r.status_code, "latency_ms": elapsed_ms, "body": parsed}


async def run_tests(base_url: str, judge_path: Path) -> list[dict[str, Any]]:
    judge_spec = json.loads(judge_path.read_text(encoding="utf-8"))
    endpoint = judge_spec["endpoint"]
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for t in judge_spec["tests"]:
            r = await make_request(client, base_url, endpoint, t.get("input"))
            results.append({"id": t["id"], "type": t["type"], "weight": t.get("weight", 1.0), "input": t.get("input"), "expected": t.get("expected"), "observed": r})
    return results


def score_with_llm(results: list[dict[str, Any]], rubric_md: str) -> dict[str, Any]:
    """Send the test results + rubric to Claude. Get back a per-test score and overall."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"status": "skipped", "reason": "ANTHROPIC_API_KEY not set — manual review needed", "tests": results}

    client = anthropic.Anthropic(api_key=api_key)
    user = (
        "# Rubric\n\n"
        + rubric_md
        + "\n\n# Test results to score\n\n"
        + "Below is one record per test: id, type, weight, the request input, the\n"
        + "expected criteria from the spec, and what the service actually returned\n"
        + "(observed). Score each test 0-10 against the rubric. Be strict on\n"
        + "correctness and faithfulness; lenient on style. Output via the\n"
        + "submit_grade tool.\n\n"
        + "```json\n" + json.dumps(results, indent=2)[:30000] + "\n```\n"
    )
    tools = [
        {
            "name": "submit_grade",
            "description": "Submit per-test scores plus a written critique.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "scores": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "score": {"type": "integer", "minimum": 0, "maximum": 10},
                                "reasoning": {"type": "string"},
                            },
                            "required": ["id", "score", "reasoning"],
                        },
                    },
                    "overall_critique": {"type": "string"},
                },
                "required": ["scores", "overall_critique"],
            },
        }
    ]
    resp = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=4096,
        system=(
            "You are a strict reviewer for a system-design course. "
            "Score test results against the rubric. Cite specific evidence "
            "(observed body fields, status codes, latency) in each reasoning."
        ),
        tools=tools,
        tool_choice={"type": "tool", "name": "submit_grade"},
        messages=[{"role": "user", "content": user}],
    )
    grade: dict[str, Any] = {}
    for block in resp.content:
        if block.type == "tool_use" and block.name == "submit_grade":
            grade = dict(block.input)
            break
    if not grade:
        return {"status": "error", "reason": "judge did not invoke submit_grade", "tests": results}

    by_id = {s["id"]: s for s in grade["scores"]}
    weighted_sum = 0.0
    total_weight = 0.0
    for r in results:
        s = by_id.get(r["id"])
        w = float(r["weight"])
        total_weight += w
        if s is not None:
            weighted_sum += float(s["score"]) * w
    return {
        "status": "graded",
        "weighted_total": round(weighted_sum, 2),
        "weighted_max": round(total_weight * 10, 2),
        "percent": round(100 * weighted_sum / (total_weight * 10), 1) if total_weight else 0.0,
        "tests": [{**r, "score": by_id.get(r["id"], {}).get("score"), "reasoning": by_id.get(r["id"], {}).get("reasoning")} for r in results],
        "overall_critique": grade["overall_critique"],
    }


async def amain():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Base URL of the deployed service (e.g. https://my-rag.fly.dev)")
    parser.add_argument("--branch", required=True, help="design/* branch name (e.g. design/01-semantic-search)")
    parser.add_argument("--repo-root", default=".", help="Path to the course repo (where grading/<slug>/ lives)")
    parser.add_argument("--out", default="judge-result.json")
    args = parser.parse_args()

    slug = args.branch.replace("/", "-")
    grading_dir = Path(args.repo_root) / "grading" / slug
    judge_path = grading_dir / "judge.json"
    rubric_path = grading_dir / "rubric.md"
    if not judge_path.exists():
        sys.stderr.write(f"missing {judge_path}\n")
        sys.exit(2)
    rubric = rubric_path.read_text(encoding="utf-8") if rubric_path.exists() else "(no rubric — judge with general engineering rigor)"

    print(f"→ probing {args.url} with {len(json.loads(judge_path.read_text())['tests'])} tests", file=sys.stderr)
    results = await run_tests(args.url, judge_path)
    print(f"→ judging via {JUDGE_MODEL}", file=sys.stderr)
    grade = score_with_llm(results, rubric)
    Path(args.out).write_text(json.dumps(grade, indent=2), encoding="utf-8")
    print(json.dumps(grade, indent=2))
    if grade.get("status") == "graded" and grade["percent"] < 60:
        sys.exit(1)
    return 0


if __name__ == "__main__":
    asyncio.run(amain())
