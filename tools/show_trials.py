"""Print the trials of one canonical v1 case for a variant: the ticket, the expected answer, and each recorded output with its grade.

    python tools/show_trials.py t001               the five trials of variant A
    python tools/show_trials.py t001 --variant B

Replay only (reads recordings/triage). A trial passes when category and urgent are both right (the `match` grader).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.casegrades import canonical_cases, grade_output  # noqa: E402
from evalkit.replay import ReplayMiss, Store  # noqa: E402
from product import triage  # noqa: E402


def trials_of(case_id, variant="A"):
    case = next((c for c in canonical_cases() if c["id"] == case_id), None)
    if case is None:
        raise SystemExit(f"{case_id} is not a case of canonical dataset v1")
    store = Store.load("triage")
    key = triage.build_request(variant, case["text"])["key"]
    rows = []
    for t in range(1, 6):
        try:
            out = store.lookup(key, t)["output"]
            rows.append((t, out, grade_output(out, case["expected"])))
        except ReplayMiss:
            rows.append((t, None, None))
    return case, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id")
    ap.add_argument("--variant", default="A")
    a = ap.parse_args()
    case, rows = trials_of(a.case_id, a.variant)
    print(f"case {case['id']} ({case['split']}), variant {a.variant}")
    print(f"ticket: {case['text']}")
    print(f"expected: {case['expected']['category']}, urgent {str(case['expected']['urgent']).lower()}")
    for t, out, g in rows:
        shown = "not recorded" if out is None else " ".join(out.split())
        print(f"  trial {t}: {'pass' if g else 'FAIL' if g is not None else '-'}  {shown}")
    done = [g for _, _, g in rows if g is not None]
    if done:
        print(f"grades: {done}; case mean {sum(done) / len(done):.1f}")


if __name__ == "__main__":
    main()
