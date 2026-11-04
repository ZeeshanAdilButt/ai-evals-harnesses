"""Challenge 5, part 2: compare judges on dev with a rule written before you look, report the choice once on test.

Fail is the positive class. The shipped commands do the reading and the bookkeeping; you write the two decisions:
  tpr_tnr(expert, judge)     the four counts and the two rates for one judge on one split
  choose_judge(dev_rows)     the rule: drop every judge with TPR under 0.85, then take the highest TNR

Run the commands, not this file:
  python -m evalkit judge-eval --judge v1 --split dev        (also v2, v3 and your builder id; each writes runs/judge-dev/<id>.json)
  python -m evalkit judge-eval --all --split dev             (read all 14 recorded judges once)
  python -m evalkit choose                                   (applies your rule to runs/judge-dev/ and writes choice.json)
  python -m evalkit judge-eval --split test                  (runs once, for the choice, and writes the lock)
  python -m evalkit judge-probes --judge J                   (position, length and self-preference next to the rerun reference)
  python -m evalkit judge-eval --unlock                      (removes the test lock; the reset is written to results.md)
"""
from __future__ import annotations

TPR_FLOOR = 0.85


def tpr_tnr(expert, judge) -> dict:
    """expert and judge are lists of "pass" or "fail", one entry per reply, same order (a judge entry may also be None when its
    output could not be read). Fail is the positive class:
      tp: expert fail, judge fail      fn: expert fail, judge not fail
      tn: expert pass, judge pass      fp: expert pass, judge not pass
    TPR = tp / (tp + fn), the share of expert fails the judge failed. TNR = tn / (tn + fp), the share of expert passes the judge passed.
    Return {"tp", "fn", "tn", "fp", "tpr", "tnr"}."""
    raise NotImplementedError("YOUR TURN: count the four cells with fail as the positive class, then the two rates")


def choose_judge(dev_rows):
    """dev_rows: a list of dicts, one per judge you ran on dev, each with "judge" (the id), "tpr" and "tnr".
    The rule, written before you look at the numbers: keep the judges with TPR of at least 0.85; among those take the highest TNR;
    ties: the higher TPR, then the lower id (compare the id as text). Return the id, or None when no judge keeps its place."""
    raise NotImplementedError("YOUR TURN: floor on TPR first, then highest TNR, then higher TPR, then lower id")
