"""Challenge 4, part 1: audit a grader before you trust it. A grader that passes everything is the most dangerous code you own.

An audit set has known-good outputs (the grader must pass them) and known-bad ones (it must fail them), each written
by hand. `run_audit` runs the grader on both and lists every disagreement.

Fill the two YOUR TURN gaps:
  1. audit_set()                    your known-good and known-bad outputs for grade_triage_match
  2. run_audit(grader, good, bad)   run a grader on both lists and report the disagreements
"""
from __future__ import annotations

EXPECTED = {"category": "refund", "urgent": False}


def audit_set():
    """Return (good, bad): two lists of outputs for grade_triage_match(output, EXPECTED).
    good: outputs that mean {"category": "refund", "urgent": false}, written in the different harmless ways a model
    writes them (spacing, a code fence, capital letters, key order, white space). bad: outputs that must fail
    (a wrong category, an invalid one, a missing field, a string where a boolean belongs, prose, empty).
    Write at least 8 of each."""
    raise NotImplementedError("YOUR TURN: write 12 known-good and 14 known-bad outputs, with the harmless variations and the real mistakes you can think of")


def run_audit(grader, good, bad):
    """`grader` takes one output and returns True or False. Return a dict:
    {"good_n": len(good), "bad_n": len(bad), "disagreements": [{"kind": "good_failed" or "bad_passed", "output": the output}, ...], "ok": True when none}."""
    raise NotImplementedError("YOUR TURN: loop over both lists; a known-good that fails is good_failed, a known-bad that passes is bad_passed")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from graders import grade_triage_match

    g, b = audit_set()
    result = run_audit(lambda o: grade_triage_match(o, EXPECTED), g, b)
    print(f"audit: {result['good_n']} known-good, {result['bad_n']} known-bad, {len(result['disagreements'])} disagreements")
    for d in result["disagreements"]:
        print(f"  {d['kind']}: {d['output']!r}")
