"""Replay every recorded agent run and check it reproduces the recorded trajectory and final state."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.replay import ReplayMiss, Store  # noqa: E402
from product.agent.agent import run_task  # noqa: E402
from product.agent.store import load_orders  # noqa: E402

store = Store.load("agent")
tasks = {t["id"]: t for t in map(json.loads, (ROOT / "datasets/agent_tasks.jsonl").read_text(encoding="utf-8").splitlines())}
orders = load_orders(ROOT / "datasets/agent/orders.json")
ok = bad = miss = 0
for runs in sorted((ROOT / "recordings/agent-runs").glob("*.jsonl")):
    for line in runs.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        trial = r["trial"]

        def call(req, trial=trial):
            rec = store.lookup(req["key"], trial)
            return {"content": rec["content"], "stop_reason": rec["stop_reason"]}
        try:
            res = run_task(r["variant"], tasks[r["task"]], orders, call)
        except ReplayMiss:
            miss += 1
            continue
        same = res["trajectory"] == r["trajectory"] and res["final_state"] == r["final_state"]
        ok += same
        bad += not same
print(f"replayed ok {ok}, different {bad}, misses {miss}")
sys.exit(1 if bad or miss else 0)
