"""Checkpoint 2: the audit. Two constructed trials of task r01, graded by your grade_trajectory."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import agent_grade as g

task = g.load_tasks()["r01"]
GET = ("get_order", {"order_id": "FM-104201"})
POLICY = ("get_policy", {"topic": "missing_items"})
REFUND = ("issue_refund", {"order_id": "FM-104201", "amount": 8.99, "reason": "missing"})


def trial(calls):
    return {"trajectory": [{"tool": t, "input": i, "step": n + 1} for n, (t, i) in enumerate(calls)]}


good = g.grade_trajectory(trial([POLICY, GET, REFUND]), task)
twice = g.grade_trajectory(trial([GET, REFUND, REFUND]), task)
print("Different tool order:", "pass" if good["pass"] else "fail", f"(get_policy, get_order, issue_refund; rule {good['rule']})")
print("Double refund:", "pass" if twice["pass"] else "fail", f"rule {twice['rule']} ({twice['detail']})")
