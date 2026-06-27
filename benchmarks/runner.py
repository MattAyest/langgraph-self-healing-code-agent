#!/usr/bin/env python3
"""
Benchmark runner for the Coding Module.

Usage:
    python benchmarks/runner.py                        # run all questions
    python benchmarks/runner.py --ids fibonacci stack  # run specific questions
    python benchmarks/runner.py --summary              # print summary of past results

Results are appended to benchmarks/results.jsonl — one JSON line per run.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = os.environ.get("CODING_MODULE_URL", "http://localhost:8000")
QUESTIONS_FILE = Path(__file__).parent / "questions.json"
RESULTS_FILE = Path(__file__).parent / "results.jsonl"

POLL_INTERVAL = 5   # seconds between status polls
TIMEOUT = 1200      # seconds before we give up on a single task (20 min)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_questions(ids=None):
    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)
    if ids:
        questions = [q for q in questions if q["id"] in ids]
    return questions


def submit_task(prompt: str) -> str:
    resp = requests.post(f"{BASE_URL}/task", json={"prompt": prompt}, timeout=10)
    resp.raise_for_status()
    return resp.json()["task_id"]


def poll_task(task_id: str):
    resp = requests.get(f"{BASE_URL}/task/{task_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def cancel_task(task_id: str):
    """Ask the API to cancel a task so a timeout doesn't leave it running."""
    try:
        requests.post(f"{BASE_URL}/task/{task_id}/cancel", timeout=10)
    except Exception as e:
        print(f"  CANCEL ERROR: {e}")


def run_question(question: dict, run_id: str) -> dict:
    qid = question["id"]
    print(f"\n{'─' * 60}")
    print(f"  [{qid}]  difficulty={question['difficulty']}")
    print(f"  {question['prompt'][:100]}...")
    print(f"{'─' * 60}")

    start_time = time.time()
    start_iso = datetime.now(timezone.utc).isoformat()

    try:
        task_id = submit_task(question["prompt"])
    except Exception as e:
        print(f"  SUBMIT ERROR: {e}")
        return {
            "run_id": run_id,
            "question_id": qid,
            "difficulty": question["difficulty"],
            "task_id": None,
            "start_time": start_iso,
            "end_time": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - start_time, 1),
            "status": "submit_error",
            "error": str(e),
            "loop_count": 0,
            "regression_count": 0,
            "replan_count": 0,
            "files_generated": 0,
            "thoughts_count": 0,
        }

    print(f"  task_id={task_id}")
    last_node = None
    last_data = {}
    deadline = start_time + TIMEOUT

    while time.time() < deadline:
        try:
            data = poll_task(task_id)
            last_data = data
        except Exception as e:
            print(f"  POLL ERROR: {e} — retrying in {POLL_INTERVAL}s")
            time.sleep(POLL_INTERVAL)
            continue

        status = data.get("status")
        node = data.get("current_node")
        elapsed = round(time.time() - start_time, 1)

        if node != last_node:
            print(f"  {elapsed:>7.1f}s  → {node}  (loops={data.get('loop_count',0)} regressions={data.get('regression_count',0)})")
            last_node = node

        if status in ("completed", "failed", "cancelled", "exhausted"):
            end_iso = datetime.now(timezone.utc).isoformat()
            files = data.get("result") or {}
            result = {
                "run_id": run_id,
                "question_id": qid,
                "difficulty": question["difficulty"],
                "task_id": task_id,
                "start_time": start_iso,
                "end_time": end_iso,
                "elapsed_seconds": elapsed,
                "status": status,
                "error": data.get("error"),
                "loop_count": data.get("loop_count", 0),
                "regression_count": data.get("regression_count", 0),
                "replan_count": data.get("replan_count", 0),
                "files_generated": len(files),
                "thoughts_count": len(data.get("thoughts", [])),
            }
            verdict = "PASS" if status == "completed" and files else "FAIL"
            print(f"\n  {verdict}  in {elapsed}s  |  loops={result['loop_count']}  regressions={result['regression_count']}  files={result['files_generated']}")
            return result

        time.sleep(POLL_INTERVAL)

    # Timed out — cancel the task so it doesn't run on and contend with the next
    # one, and record the last-observed progress (not zeros).
    cancel_task(task_id)
    end_iso = datetime.now(timezone.utc).isoformat()
    elapsed = round(time.time() - start_time, 1)
    print(f"\n  TIMEOUT after {elapsed}s — cancelled "
          f"(last node={last_data.get('current_node')} loops={last_data.get('loop_count', 0)})")
    return {
        "run_id": run_id,
        "question_id": qid,
        "difficulty": question["difficulty"],
        "task_id": task_id,
        "start_time": start_iso,
        "end_time": end_iso,
        "elapsed_seconds": elapsed,
        "status": "timeout",
        "error": f"Timed out after {TIMEOUT}s",
        "loop_count": last_data.get("loop_count", 0),
        "regression_count": last_data.get("regression_count", 0),
        "replan_count": last_data.get("replan_count", 0),
        "files_generated": len(last_data.get("result") or {}),
        "thoughts_count": len(last_data.get("thoughts", [])),
    }


def append_result(result: dict):
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")


def print_summary(results: list[dict]):
    if not results:
        return
    print(f"\n{'═' * 70}")
    print(f"  RUN SUMMARY  ({results[0]['run_id']})")
    print(f"{'═' * 70}")
    print(f"  {'ID':<20} {'DIFF':<8} {'STATUS':<10} {'TIME':>8}  {'LOOPS':>5}  {'REGR':>5}  {'FILES':>5}")
    print(f"  {'─'*20} {'─'*8} {'─'*10} {'─'*8}  {'─'*5}  {'─'*5}  {'─'*5}")
    total_elapsed = 0
    passed = 0
    for r in results:
        verdict = "PASS" if r["status"] == "completed" and r["files_generated"] > 0 else "FAIL"
        if verdict == "PASS":
            passed += 1
        total_elapsed += r["elapsed_seconds"]
        print(f"  {r['question_id']:<20} {r['difficulty']:<8} {verdict:<10} {r['elapsed_seconds']:>7.1f}s"
              f"  {r['loop_count']:>5}  {r['regression_count']:>5}  {r['files_generated']:>5}")
    print(f"{'─' * 70}")
    print(f"  {passed}/{len(results)} passed   total time: {total_elapsed:.1f}s   avg: {total_elapsed/len(results):.1f}s")
    print(f"{'═' * 70}\n")


def print_historical_summary():
    if not RESULTS_FILE.exists():
        print("No results yet.")
        return

    runs: dict[str, list] = {}
    with open(RESULTS_FILE) as f:
        for line in f:
            r = json.loads(line.strip())
            runs.setdefault(r["run_id"], []).append(r)

    for run_id, results in sorted(runs.items()):
        ts = results[0]["start_time"][:19].replace("T", " ")
        passed = sum(1 for r in results if r["status"] == "completed" and r["files_generated"] > 0)
        total = len(results)
        avg_time = sum(r["elapsed_seconds"] for r in results) / total
        label = results[0].get("label") or ""
        label_str = f"  [{label}]" if label else ""
        print(f"  {run_id}  {ts}  {passed}/{total} passed  avg {avg_time:.1f}s{label_str}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global BASE_URL, TIMEOUT
    parser = argparse.ArgumentParser(description="Coding Module benchmark runner")
    parser.add_argument("--ids", nargs="+", help="Run only these question IDs")
    parser.add_argument("--summary", action="store_true", help="Print history of past runs and exit")
    parser.add_argument("--url", default=None, help="Override API base URL")
    parser.add_argument("--timeout", type=int, default=None,
                        help=f"Per-task timeout in seconds (default {TIMEOUT})")
    parser.add_argument("--label", default="",
                        help="Short tag stored on every result row (e.g. the code state / "
                             "fixes active) so runs are comparable later")
    args = parser.parse_args()

    if args.url:
        BASE_URL = args.url

    if args.timeout:
        TIMEOUT = args.timeout

    if args.summary:
        print_historical_summary()
        return

    questions = load_questions(args.ids)
    if not questions:
        print("No questions matched.")
        sys.exit(1)

    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\nBenchmark run: {run_id}")
    print(f"Questions:     {len(questions)}")
    print(f"API:           {BASE_URL}")
    if args.label:
        print(f"Label:         {args.label}")

    results = []
    for q in questions:
        r = run_question(q, run_id)
        r["label"] = args.label
        append_result(r)
        results.append(r)

    print_summary(results)


if __name__ == "__main__":
    main()
