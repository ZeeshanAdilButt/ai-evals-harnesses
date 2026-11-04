"""The capstone's judge step (shipped, finished): which judge verdicts exist for A's and the candidate's refund replies on dataset v2.

Decision of 2026-11-05: the capstone judges are recorded on trial 1 of every reply for every judge, and on all five reply trials only for
judge v3. A verdict is found by request key (judge prompt, ticket, reply), so a reply already judged for another purpose is found too.
A verdict that is not recorded yet is counted and named; it is never guessed. `reference/results/capstone-recordings-needed.md` lists the
exact `tools/record_judge.py` commands that fill the gaps.
"""
from __future__ import annotations

import json
from pathlib import Path

from evalkit import judges_cli, labels
from evalkit.replay import ReplayMiss, Store
from judges.parts import ALL_JUDGES
from product import reply as reply_feature
from product.judge import build_request, parse_verdict

ROOT = labels.ROOT
VARIANTS = ("A", "candidate")


def refund_cases() -> list:
    """The 72 refund tickets of canonical dataset v2 (32 from v1 and the 40 added from the broken slice)."""
    rows = [json.loads(l) for l in (ROOT / "datasets/canonical/v2/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [c for c in rows if c["expected"]["category"] == "refund"]


def reply_trials(judge: str) -> tuple:
    return (1, 2, 3, 4, 5) if judge == "v3" else (1,)


def dev_tpr(judge: str) -> float | None:
    """Dev TPR of the judge against the expert labels (the 5.8 rule's first step needs at least 0.85)."""
    ids, e, j, missing = judges_cli.split_verdicts(judge, "dev")
    fails = [x for x, y in zip(e, j) if x == "fail"]
    if missing or not fails:
        return None
    return sum(y == "fail" for x, y in zip(e, j) if x == "fail") / len(fails)


def allowed_judges() -> list:
    """The judges the 5.8 rule keeps: dev TPR of at least 0.85, from the labels in use."""
    return [j for j in ALL_JUDGES if (dev_tpr(j) or 0) >= 0.85]


def judged(judge: str, variants=VARIANTS) -> dict:
    """For each variant: the judge's verdicts on the 72 refund tickets. Returns
    {variant: {"needed": calls, "missing": calls not recorded yet, "case_rates": {ticket id: pass share over the judged trials}, "pass_rate": mean or None}}."""
    replies, verdicts = Store.load("reply"), Store.load("judge")
    cases = refund_cases()
    out = {}
    for variant in variants:
        needed = missing = 0
        rates = {}
        for c in cases:
            key = reply_feature.build_request(variant, c["text"])["key"]
            got = []
            for t in reply_trials(judge):
                needed += 1
                try:
                    text = replies.lookup(key, t)["output"]
                    got.append(parse_verdict(verdicts.lookup(build_request(judge, c["text"], text)["key"], 1)["output"]) == "pass")
                except ReplayMiss:
                    missing += 1
            if len(got) == len(reply_trials(judge)):
                rates[c["id"]] = sum(got) / len(got)
        out[variant] = {"needed": needed, "missing": missing, "case_rates": rates,
                        "pass_rate": (sum(rates.values()) / len(rates)) if len(rates) == len(cases) else None}
    return out


def status_lines(judge: str) -> list:
    """One line per variant: recorded, or 'not recorded yet' with the number of calls and the command that records them."""
    lines = []
    for variant, d in judged(judge).items():
        if d["missing"]:
            lines.append(f"not recorded yet: judge {judge} on {variant} refund replies, {d['missing']} of {d['needed']} verdicts "
                         "(see reference/results/capstone-recordings-needed.md)")
        else:
            lines.append(f"judge {judge} on {variant} refund replies: all {d['needed']} verdicts recorded")
    return lines
