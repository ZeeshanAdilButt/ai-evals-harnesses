"""Challenge 11, part 2: the report check. It reads report.md and compares the fenced `numbers` block with your 11.2 results
(../part-1-release-suite/summary.json) and your 5.8 test report (runs/judge-test.json). Shipped; the report itself is your own writing.

    python challenges/challenge-11-capstone/part-2-report/check_report.py            prints every problem it finds, exit 1 if any

The numbers block is YAML: `key: value` lines inside a fence that starts with three backticks and the word numbers.
Fractions are written as decimals (0.891), counts as integers, ids and verdicts as words. A number is right when it is within 0.005 of the
results; a word must be equal. A judge number that is not recorded yet is written as: not recorded yet.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUMMARY = ROOT / "challenges" / "challenge-11-capstone" / "part-1-release-suite" / "summary.json"
JUDGE_TEST = ROOT / "runs" / "judge-test.json"
NOT_YET = "not recorded yet"
SECTIONS_2_TO_5 = ("dataset_v2_hash", "triage_pass_A", "triage_pass_cand", "triage_diff", "triage_diff_lo", "triage_diff_hi", "triage_verdict",
                   "reply_pass_A", "reply_pass_cand", "reply_diff", "reply_diff_lo", "reply_diff_hi", "reply_verdict", "reply_weak_slice", "reply_slice_n",
                   "reply_slice_diff", "reply_slice_lo", "reply_slice_hi", "agent_pass1_A", "agent_pass4_A", "agent_pass1_cand", "agent_pass4_cand",
                   "mustpass_n", "mustpass_fail_task", "mustpass_fail_trials")
SECTIONS_6_TO_7 = ("judge_id", "judge_test_tp", "judge_test_fn", "judge_test_tn", "judge_test_fp", "judge_test_tpr", "judge_test_tnr",
                   "reply_judged_n", "reply_judge_pass_A", "reply_judge_pass_cand",
                   "cost1k_A", "cost1k_cand", "p95_A_ms", "p95_cand_ms", "budget_cost_per_1k", "budget_p95_ms", "gate_exit_cand")


def expected(summary: dict, judge_test: dict | None) -> dict:
    s, w = summary, summary["reply_weak_slice"]
    jr, c = s["judge_result"], s["cost"]
    out = {"dataset_v2_hash": s["dataset_v2_hash"],
           "triage_pass_A": s["triage"]["A"], "triage_pass_cand": s["triage"]["candidate"], "triage_diff": s["triage"]["diff"],
           "triage_diff_lo": s["triage"]["lo"], "triage_diff_hi": s["triage"]["hi"], "triage_verdict": s["triage"]["verdict"],
           "reply_pass_A": s["reply"]["A"], "reply_pass_cand": s["reply"]["candidate"], "reply_diff": s["reply"]["diff"],
           "reply_diff_lo": s["reply"]["lo"], "reply_diff_hi": s["reply"]["hi"], "reply_verdict": s["reply"]["verdict"],
           "reply_weak_slice": w["slice"], "reply_slice_n": w["n"], "reply_slice_diff": w["diff"], "reply_slice_lo": w["lo"], "reply_slice_hi": w["hi"],
           "agent_pass1_A": s["agent"]["pass1_A"], "agent_pass4_A": s["agent"]["pass4_A"], "agent_pass1_cand": s["agent"]["pass1_candidate"],
           "agent_pass4_cand": s["agent"]["pass4_candidate"], "mustpass_n": s["mustpass"]["n"], "mustpass_fail_task": s["mustpass"]["fail_task"],
           "mustpass_fail_trials": s["mustpass"]["fail_trials"],
           "cost1k_A": c["cost1k_A"], "cost1k_cand": c["cost1k_candidate"], "p95_A_ms": c["p95_A_ms"], "p95_cand_ms": c["p95_candidate_ms"],
           "budget_cost_per_1k": c["budget_cost_per_1k"], "budget_p95_ms": c["budget_p95_ms"], "gate_exit_cand": s["gate"]["exit"],
           "reply_judged_n": jr["judged_n"] if jr["recorded"] else NOT_YET,
           "reply_judge_pass_A": jr["pass_A"] if jr["pass_A"] is not None else NOT_YET,
           "reply_judge_pass_cand": jr["pass_candidate"] if jr["pass_candidate"] is not None else NOT_YET}
    if judge_test:
        out.update(judge_id=judge_test["judge"], judge_test_tp=judge_test["tp"], judge_test_fn=judge_test["fn"], judge_test_tn=judge_test["tn"],
                   judge_test_fp=judge_test["fp"], judge_test_tpr=judge_test["tpr"], judge_test_tnr=judge_test["tnr"])
    return out


def numbers_block(text: str) -> dict:
    m = re.search(r"^```numbers\s*\n(.*?)^```", text, flags=re.M | re.S)
    if not m:
        raise ValueError("report.md has no fenced numbers block (three backticks and the word numbers)")
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("the numbers block must be key: value lines")
    return data


def compare(block: dict, want: dict, keys) -> list:
    problems = []
    for k in keys:
        if k not in want:
            continue
        got = block.get(k)
        if got is None or str(got).startswith("(fill in"):
            problems.append(f"numbers: {k} is missing")
        elif isinstance(want[k], (int, float)) and not isinstance(want[k], bool):
            if not isinstance(got, (int, float)) or abs(float(got) - float(want[k])) > 0.005:
                problems.append(f"numbers: {k} is {got}, your results say {want[k]}")
        elif str(got) != str(want[k]):
            problems.append(f"numbers: {k} is {got}, your results say {want[k]}")
    return problems


def load_inputs():
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    judge_test = json.loads(JUDGE_TEST.read_text(encoding="utf-8")) if JUDGE_TEST.exists() else None
    return summary, judge_test


def check(report: Path = HERE / "report.md") -> list:
    summary, judge_test = load_inputs()
    text = report.read_text(encoding="utf-8")
    try:
        block = numbers_block(text)
    except ValueError as err:
        return [str(err)]
    want = expected(summary, judge_test)
    return compare(block, want, SECTIONS_2_TO_5 + SECTIONS_6_TO_7)


def main() -> int:
    problems = check()
    for p in problems:
        print(p)
    print("report check:", "OK, every number in the numbers block matches your results" if not problems else f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
