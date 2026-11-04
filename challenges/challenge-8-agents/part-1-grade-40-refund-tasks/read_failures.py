"""Checkpoint 3: read the failures. It only reads the recordings and the shipped helpers.
Add --table to print the label table for results.md."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import agent_grade as g

tasks = g.load_tasks()
trials = {(t["task"], t["trial"]): t for t in g.load_runs("A")}
rows = g.grade_all("A")
failed = [r for r in rows if not r["passed"]]

if "--table" in sys.argv:
    print("| task | trial | label |")
    print("|---|---|---|")
    for r in failed:
        label = "simulator" if g.is_simulator_failure(trials[(r["task"], r["trial"])], tasks[r["task"]]) else "agent"
        print(f"| {r['task']} | {r['trial']} | {label} |")
    raise SystemExit

print("pass^k by hand, tasks r12 and r14 of variant A")
per = g.passes_per_task(rows)
for tid in ("r12", "r14"):
    c = per[tid]
    print(f"  {tid}: {c} of 5 pass, pass^1 {g.pass_hat_k(c, 5, 1):.2f}, pass^2 {g.pass_hat_k(c, 5, 2):.2f}, pass^4 {g.pass_hat_k(c, 5, 4):.2f}")

print("first failing step")
for tid, n in (("r09", 2), ("r10", 1), ("r13", 1)):
    step, why = g.first_failing_step_of(trials[(tid, n)], tasks[tid])
    print(f"  {tid}/{n}: step {step}, {why}")

print("failed trials where the customer ended the task")
for tid in sorted({r["task"] for r in failed}):
    mine = [r["trial"] for r in failed if r["task"] == tid]
    ended = [n for n in mine if g.is_simulator_failure(trials[(tid, n)], tasks[tid])]
    print(f"  {tid}: failed {len(mine)}, customer ended the task in {len(ended)}")

print("last two calls of r13, trial 1")
for call in trials[("r13", 1)]["trajectory"][-2:]:
    print(f"  {call['tool']}: {call['input']['question'][:70]}")
print("  gives_up_after:", tasks["r13"]["customer"]["gives_up_after"])

print("your grades against datasets/reference_grades/agent.jsonl")
ref = [json.loads(l) for l in ROOT / "datasets/reference_grades/agent.jsonl".read_text(encoding="utf-8").splitlines()]
for v in "AB":
    mine = g.grade_all(v)
    want = [r for r in ref if r["variant"] == v]
    key = lambda r: (r["state_ok"], r["traj_pass"], r["traj_rule"], r["passed"])
    differ = [(a["task"], a["trial"]) for a, b in zip(mine, want) if key(a) != key(b)]
    print(f"  {v}: {len(mine)} trials, {len(differ)} differ from the reference")
