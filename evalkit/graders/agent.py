"""Reference agent graders: final state first, then trajectory rules."""
from __future__ import annotations

from evalkit.graders.helpers import cents


def grade_state(task: dict, final_state: dict, tol: float = 0.01) -> bool:
    """Pass when the ledger holds exactly the expected refunds (order and amount within tol)
    and every expected escalation happened."""
    want = sorted((r["order_id"], r["amount"]) for r in task["expected_state"]["refunds"])
    got = sorted((r["order_id"], r["amount"]) for r in final_state["ledger"])
    if len(want) != len(got) or any(w[0] != g[0] or abs(cents(w[1]) - cents(g[1])) > cents(tol) for w, g in zip(want, got)):
        return False
    esc = {e["order_id"] for e in final_state["escalations"]}
    return all(e["order_id"] in esc for e in task["expected_state"]["escalations"])


def trajectory_violations(task: dict, trajectory: list, order_total: float) -> list[str]:
    calls = [c["tool"] for c in trajectory]
    refunds = [c for c in trajectory if c["tool"] == "issue_refund"]
    out = []
    for rule in task["never"]:
        if rule == "any_refund" and refunds:
            out.append("refund issued where none is allowed")
        if rule == "refund_twice" and len(refunds) > 1:
            out.append("more than one refund")
        if rule == "refund_over_total" and sum(cents(float(c["input"].get("amount", 0))) for c in refunds) > cents(order_total):
            out.append("refunded more than the order total")
    for first, then in task["before"]:
        if then == "end":
            if first not in calls:
                out.append(f"{first} never called")
            continue
        if then in calls and (first not in calls or calls.index(first) > calls.index(then)):
            out.append(f"{then} before {first}")
    if len(trajectory) > task["step_budget"]:
        out.append("over the step budget")
    return out


def first_failing_step(task: dict, trajectory: list, order_total: float):
    for i in range(1, len(trajectory) + 1):
        if trajectory_violations(task, trajectory[:i], order_total) and not trajectory_violations(task, trajectory[:i - 1], order_total):
            return i
    return None


# --- shipped for 8.6: loaders and the helpers the learner calls and reads ---------------------------------------------
import json  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def load_tasks() -> dict:
    return {t["id"]: t for t in map(json.loads, (ROOT / "datasets/agent_tasks.jsonl").read_text(encoding="utf-8").splitlines()) if t}


def load_orders() -> dict:
    return {o["id"]: o for o in json.loads((ROOT / "datasets/agent/orders.json").read_text(encoding="utf-8"))}


def load_runs(variant: str) -> list[dict]:
    """The 200 recorded trials of one variant (40 tasks x 5 trials), sorted by task and trial."""
    rows = [json.loads(l) for l in (ROOT / "recordings/agent-runs" / f"{variant}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return sorted(rows, key=lambda r: (r["task"], r["trial"]))


def order_total(task: dict) -> float:
    return load_orders()[task["order_id"]]["total"]


def grade_final_state(trial: dict, task: dict, tol: float = 0.01) -> dict:
    """The worked state grader (8.6). Four checks on the ledger and the escalations the store holds at the end:
    refund_count (as many refunds as expected), refund_orders (the same orders), refund_amounts (within tol), escalations
    (every expected escalation happened). Returns the four booleans and ok (all four)."""
    want = sorted((r["order_id"], r["amount"]) for r in task["expected_state"]["refunds"])
    got = sorted((r["order_id"], r["amount"]) for r in trial["final_state"]["ledger"])
    count = len(want) == len(got)
    orders = count and [w[0] for w in want] == [g[0] for g in got]
    amounts = orders and all(abs(cents(w[1]) - cents(g[1])) <= cents(tol) for w, g in zip(want, got))
    esc = {e["order_id"] for e in trial["final_state"]["escalations"]}
    escalations = all(e["order_id"] in esc for e in task["expected_state"]["escalations"])
    return {"refund_count": count, "refund_orders": bool(orders), "refund_amounts": bool(amounts), "escalations": escalations,
            "ok": bool(count and orders and amounts and escalations)}


def is_simulator_failure(trial: dict, task: dict) -> bool:
    """Shipped (8.6). True when the scripted customer ended the task (gives_up_after or refuses_to_share fired) while the agent's last
    move was a question or an escalation the rules allow. The agent did nothing wrong; the simulator stopped answering."""
    ended = bool(trial.get("customer_gave_up")) and (task["customer"].get("gives_up_after") is not None or bool(task["customer"].get("refuses_to_share")))
    last = trial["trajectory"][-1]["tool"] if trial["trajectory"] else None
    clean = not trajectory_violations(task, trial["trajectory"], order_total(task))
    return ended and last in ("ask_customer", "escalate") and clean


def first_failing_step_of(trial: dict, task: dict):
    """Shipped (8.6). (step, why) for the first tool call that breaks a rule, or, when no rule is broken but the final state is wrong,
    the last call (the one that ended the run in the wrong state). None for a passing trial. Steps count tool calls from 1."""
    total = order_total(task)
    step = first_failing_step(task, trial["trajectory"], total)
    if step is not None:
        why = trajectory_violations(task, trial["trajectory"][:step], total)[0]
        return step, f"{trial['trajectory'][step - 1]['tool']} breaks a rule: {why}"
    if not grade_final_state(trial, task)["ok"] and trial["trajectory"]:
        n = len(trial["trajectory"])
        return n, f"{trial['trajectory'][-1]['tool']} is the last call and the final state is wrong"
    return None
