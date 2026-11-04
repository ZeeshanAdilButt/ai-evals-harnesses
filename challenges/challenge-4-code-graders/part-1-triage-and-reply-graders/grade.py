"""Challenge 4, part 1: grade variant A or B on canonical dataset v1 with YOUR graders, and print the tables.

    python challenges/challenge-4-code-graders/part-1-triage-and-reply-graders/grade.py --variant A

Replay only: it reads the recorded outputs of trial 1 (the first of the five recorded trials) and calls no model.
Triage and reply run on canonical dataset v1 (160 cases), never on your own dataset from chapter 3.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import graders  # noqa: E402
from evalkit.graders.helpers import confusion_matrix  # noqa: E402
from evalkit.replay import Store  # noqa: E402
from product import reply, triage  # noqa: E402

CATEGORIES = graders.CATEGORIES


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def compact(expected):
    """The whole expected answer as compact JSON, no spaces: {"category":"refund","urgent":false}."""
    return json.dumps({"category": expected["category"], "urgent": expected["urgent"]}, separators=(",", ":"))


def cases():
    return [json.loads(l) for l in (ROOT / "datasets/canonical/v1/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def checks():
    return {r["id"]: r for r in map(json.loads, (ROOT / "datasets/reply_checks.jsonl").read_text(encoding="utf-8").splitlines())}


def triage_numbers(variant, g=graders, trial=1):
    """All the triage numbers for one variant, computed with the graders module `g`."""
    store = Store.load("triage")
    cs = cases()
    schema = match = norm_cat = exact_cat = compact_eq = 0
    cat_pairs, urg = [], {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for c in cs:
        out = store.lookup(triage.build_request(variant, c["text"])["key"], trial)["output"]
        exp = c["expected"]
        ok_schema = g.grade_triage_schema(out)
        schema += ok_schema
        match += g.grade_triage_match(out, exp)
        compact_eq += out == compact(exp)
        parsed = g._parse(out) if ok_schema else None
        pred_cat = g.normalise(parsed["category"]) if parsed else "invalid"
        pred_urgent = parsed["urgent"] if parsed else False
        exact_cat += bool(parsed) and parsed["category"] == exp["category"]
        norm_cat += pred_cat == exp["category"]
        cat_pairs.append((exp["category"], pred_cat))
        truth = exp["urgent"]
        urg["tp"] += truth and pred_urgent
        urg["fn"] += truth and not pred_urgent
        urg["fp"] += (not truth) and pred_urgent
        urg["tn"] += (not truth) and not pred_urgent
    n = len(cs)
    cat = confusion_matrix(cat_pairs, CATEGORIES)
    recall = {t: pct(cat[t][t], sum(cat[t].values())) for t in CATEGORIES}
    return {"n": n, "schema": pct(schema, n), "match": pct(match, n), "compact": pct(compact_eq, n), "exact_category": pct(exact_cat, n),
            "normalised_category": pct(norm_cat, n), "urgent": urg, "category": cat, "recall": recall,
            "weak_class": min(CATEGORIES, key=lambda t: (recall[t], t))}


def reply_numbers(variant, g=graders, trial=1):
    store = Store.load("reply")
    ck = checks()
    contains = days = amount = must = 0
    n_days = n_amount = n_must = 0
    for c in cases():
        r = ck[c["id"]]
        out = store.lookup(reply.build_request(variant, c["text"])["key"], trial)["output"]
        ok_contains = g.grade_reply_contains(out, r["must_contain"], r["must_not_contain"])
        contains += ok_contains
        ok_days = None
        if r["refund_days"] is not None:
            ok_days = g.grade_reply_refund_days(out, r["refund_days"])
            n_days += 1
            days += ok_days
        if r["refund_amount"] is not None:
            n_amount += 1
            amount += g.grade_reply_amount(out, r["refund_amount"], 0.01)
        if r["must_pass"]:
            n_must += 1
            must += ok_contains and bool(ok_days)
    return {"n": len(ck), "contains": pct(contains, len(ck)), "days": pct(days, n_days), "days_n": n_days, "amount": pct(amount, n_amount),
            "amount_n": n_amount, "must_pass": pct(must, n_must), "must_pass_n": n_must}


def render(variant, t, r):
    L = [f"Variant {variant}, canonical v1, trial 1 ({t['n']} cases)", "",
         f"schema pass: {t['schema']}%",
         f"whole-string match against the compact expected JSON: {t['compact']}%",
         f"category exact (letter for letter): {t['exact_category']}%",
         f"category normalised: {t['normalised_category']}%",
         f"category and urgent match: {t['match']}%", "",
         "Urgent (positive class): TP {tp}, FP {fp}, FN {fn}, TN {tn}".format(**t["urgent"]), "",
         "| true \\ predicted | " + " | ".join(CATEGORIES) + " | invalid |", "|---" * (len(CATEGORIES) + 2) + "|"]
    for c in CATEGORIES:
        L.append(f"| {c} | " + " | ".join(str(t["category"][c][p]) for p in list(CATEGORIES) + ["invalid"]) + " |")
    L += ["", "Recall by category: " + ", ".join(f"{c} {t['recall'][c]}" for c in CATEGORIES), f"Lowest recall: {t['weak_class']}", "",
          f"reply must and must not contain: {r['contains']}% of {r['n']}",
          f"reply refund days exact (7): {r['days']}% of {r['days_n']}",
          f"reply amount within 0.01: {r['amount']}% of {r['amount_n']}",
          f"reply must-pass cases (contains and days): {r['must_pass']}% of {r['must_pass_n']}"]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True, choices=["A", "B"])
    a = ap.parse_args()
    try:
        print(render(a.variant, triage_numbers(a.variant), reply_numbers(a.variant)))
    except NotImplementedError as err:
        print(f"{err}\nFill the gaps in graders.py first.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
