"""Record the refund agent: every task, every trial, live once. Author only.

    python tools/record_agent.py --variants A B --trials 5

Each model call of a trial is one recording line (key, trial) with the full content blocks, so a
replay of the trial asks for exactly the recorded requests. A summary of each run goes to
recordings/agent-runs/<variant>.jsonl; finished (task, trial) pairs are skipped on a rerun.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from product.agent.agent import run_task  # noqa: E402
from product.agent.store import load_orders  # noqa: E402

lock = threading.Lock()


def live_caller(client, variant, trial, out):
    def call(req):
        for attempt in range(8):
            try:
                t0 = time.perf_counter()
                msg = client.messages.create(model=req["model"], system=req["system"], messages=req["messages"],
                                             tools=req["tools"], **req["params"])
                ms = round((time.perf_counter() - t0) * 1000)
                break
            except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError):
                time.sleep(min(60, 2 ** attempt * 2))
        else:
            raise RuntimeError("call failed after retries")
        blocks = [b.model_dump(exclude_none=True) for b in msg.content]
        line = {"key": req["key"], "trial": trial, "feature": "agent", "variant": variant, "model": msg.model,
                "recorded_at": date.today().isoformat(), "tokens_in": msg.usage.input_tokens,
                "tokens_out": msg.usage.output_tokens, "latency_ms": ms, "latency_valid": True,
                "stop_reason": msg.stop_reason, "content": blocks,
                "output": "".join(b.get("text", "") for b in blocks if b.get("type") == "text")}
        with lock, out.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return {"content": blocks, "stop_reason": msg.stop_reason}
    return call


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="+", required=True)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    tasks = [json.loads(l) for l in (ROOT / "datasets/agent_tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.limit:
        tasks = tasks[: a.limit]
    orders = load_orders(ROOT / "datasets/agent/orders.json")
    client = anthropic.Anthropic()
    folder = ROOT / "recordings" / "agent"
    folder.mkdir(parents=True, exist_ok=True)
    for variant in a.variants:
        out = folder / f"{variant}.jsonl"
        runs = ROOT / "recordings" / "agent-runs" / f"{variant}.jsonl"
        runs.parent.mkdir(parents=True, exist_ok=True)
        done = set()
        if runs.exists():
            for l in runs.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    r = json.loads(l); done.add((r["task"], r["trial"]))
        jobs = [(t, k) for k in range(1, a.trials + 1) for t in tasks if (t["id"], k) not in done]
        print(f"{variant}: {len(jobs)} runs to record", flush=True)

        def one(job):
            t, k = job
            res = run_task(variant, t, orders, live_caller(client, variant, k, out))
            res["trial"] = k
            with lock, runs.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(res, ensure_ascii=False, sort_keys=True) + "\n")
            return res["stop"]

        with ThreadPoolExecutor(max_workers=6) as pool:
            for stop in pool.map(one, jobs):
                pass
        print(f"{variant}: done", flush=True)


if __name__ == "__main__":
    main()
