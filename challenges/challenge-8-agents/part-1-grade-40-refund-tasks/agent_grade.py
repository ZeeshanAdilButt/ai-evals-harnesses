"""Challenge 8, part 1: grade 40 refund tasks, five trials each. "The message looked fine. Check the ledger."

Shipped and read, not written (evalkit/graders/agent.py and evalkit/stats.py):
  grade_final_state(trial, task)       the worked state grader: four checks on the ledger and the escalations
  pass_hat_k(c, n, k)                  pass^k for one task: comb(c, k) / comb(n, k)
  first_failing_step_of(trial, task)   (step, why) of the first tool call that breaks a rule or leaves the wrong state
  is_simulator_failure(trial, task)    the scripted customer ended the task while the agent's last move was allowed

Fill the one YOUR TURN gap:
  grade_trajectory(trial, task)        read the task's `never`, `before` and `step_budget`; return the first broken rule

A trial dict has `trajectory` (the tool calls in order: tool, input, step), `final_state` (ledger, escalations), `customer_gave_up`.
A task dict has `never`, `before`, `step_budget`, `expected_state`, `customer`, `order_id`.

Run it:  python challenges/challenge-8-agents/part-1-grade-40-refund-tasks/agent_grade.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from evalkit.graders.agent import (  # noqa: E402,F401  (shipped)
    first_failing_step_of, grade_final_state, is_simulator_failure, load_orders, load_runs, load_tasks, order_total)
from evalkit.stats import pass_hat_k  # noqa: E402,F401  (shipped)


def grade_trajectory(trial, task):
    """Check the three kinds of rule, in this order, and return the first one broken as a dict
    {"pass": bool, "rule": "R1", "R2", "R3" or None, "detail": a short sentence}.

    R1, task["never"]: "any_refund" (no issue_refund call at all), "refund_twice" (more than one issue_refund call),
        "refund_over_total" (the refund amounts add up to more than order_total(task) + 0.01).
    R2, task["before"]: a list of [first, then] pairs of tool names. If `then` was called, `first` must have been called earlier. If `then` is
        the word "end" the pair means `first` must be called at some point.
    R3, task["step_budget"]: more tool calls than the budget breaks it.

    Only the order of calls matters for R2, not which other tools were used, so a good trial that looks things up in a different order passes."""
    raise NotImplementedError("YOUR TURN: R1 from never, then R2 from before, then R3 from step_budget; return the first broken rule or {'pass': True, 'rule': None, ...}")


def grade_all(variant, trajectory_grader=None):
    """Grade every recorded trial of a variant (given). One dict per trial, sorted by task and trial; the same input always gives the same output."""
    trajectory_grader = trajectory_grader or grade_trajectory
    tasks = load_tasks()
    rows = []
    for t in load_runs(variant):
        task = tasks[t["task"]]
        state = grade_final_state(t, task)
        traj = trajectory_grader(t, task)
        failing = first_failing_step_of(t, task)
        rows.append({"variant": variant, "task": t["task"], "trial": t["trial"], "state_ok": state["ok"], "traj_pass": traj["pass"],
                     "traj_rule": traj["rule"], "passed": bool(state["ok"] and traj["pass"]),
                     "first_failing_step": failing[0] if failing else None, "simulator": is_simulator_failure(t, task) and not (state["ok"] and traj["pass"])})
    return rows


def passes_per_task(rows):
    out = {}
    for r in rows:
        out[r["task"]] = out.get(r["task"], 0) + int(r["passed"])
    return out


def suite_pass_hat_k(rows, k, n=5):
    per = passes_per_task(rows)
    return sum(pass_hat_k(c, n, k) for c in per.values()) / len(per)


def write_runs(variant, rows):
    """Write runs/agent40-<variant>/trials.jsonl in the run format, so `python -m evalkit stats passk runs/agent40-A --k 4` works."""
    out = ROOT / "runs" / f"agent40-{variant}"
    out.mkdir(parents=True, exist_ok=True)
    lines = [{"feature": "agent", "case_id": r["task"], "variant": variant, "trial": r["trial"], "status": "ok", "passed": r["passed"],
              "grades": {"agent_state": r["state_ok"], "agent_trajectory": r["traj_pass"]}} for r in rows]
    (out / "trials.jsonl").write_text("".join(json.dumps(l, sort_keys=True) + "\n" for l in lines), encoding="utf-8")
    return out


def main():
    for v in "AB":
        rows = grade_all(v)
        write_runs(v, rows)
        per = passes_per_task(rows)
        print(f"{v}: {len(rows)} trials, {sum(r['passed'] for r in rows)} passed; state failures {sum(not r['state_ok'] for r in rows)}, "
              f"trajectory failures {sum(not r['traj_pass'] for r in rows)}")
        print(f"   pass^1 {100 * suite_pass_hat_k(rows, 1):.1f}%  pass^4 {100 * suite_pass_hat_k(rows, 4):.1f}%  tasks below 5 of 5: "
              + ", ".join(f"{t} ({c})" for t, c in sorted(per.items()) if c < 5))
        sims = sorted({(r["task"]) for r in rows if r["simulator"]})
        print(f"   failed trials where the scripted customer gave up: tasks {', '.join(sims) or 'none'}")


if __name__ == "__main__":
    main()
