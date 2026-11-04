"""Print the 7.8 tuning rounds: triage on canonical v1, one trial per case, dev (120 cases) and held-out (40 cases).

    python tools/tuning_rounds.py

Round 0 is variant A trial 1. Rounds 1 to 5 are variants T1 to T5 (prompt A plus 1 to 5 rules written from A's dev errors),
recorded with the tag `tuning`. A round that is not recorded yet prints "not recorded" and the tool goes on.
A trial passes when category and urgent are both right.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.casegrades import canonical_cases, grade_output  # noqa: E402
from evalkit.replay import ReplayMiss, Store  # noqa: E402
from product import triage  # noqa: E402

ROUNDS = ["A", "T1", "T2", "T3", "T4", "T5"]


def score_round(variant, cases=None, store=None):
    """(dev %, held-out %, missing) for one variant. missing is the number of cases with no recording; scores are None unless all 160 are recorded."""
    cases = cases or canonical_cases()
    store = store or Store.load("triage")
    grades, missing = {"dev": [], "heldout": []}, 0
    for c in cases:
        try:
            out = store.lookup(triage.build_request(variant, c["text"])["key"], 1)["output"]
            grades[c["split"]].append(grade_output(out, c["expected"]))
        except ReplayMiss:
            missing += 1
    if missing:
        return None, None, missing
    return (round(100 * sum(grades["dev"]) / len(grades["dev"]), 1), round(100 * sum(grades["heldout"]) / len(grades["heldout"]), 1), 0)


def rounds():
    cases, store = canonical_cases(), Store.load("triage")
    return [(i, v) + score_round(v, cases, store) for i, v in enumerate(ROUNDS)]


def main():
    print("round | variant | dev (120 cases) | held-out (40 cases) | gap")
    for i, v, dev, held, missing in rounds():
        if dev is None:
            print(f"{i:>5} | {v:<7} | not recorded ({missing} of 160 cases have no recording yet)")
        else:
            print(f"{i:>5} | {v:<7} | {dev:>6.1f}% | {held:>6.1f}% | {dev - held:+.1f}")


if __name__ == "__main__":
    main()
