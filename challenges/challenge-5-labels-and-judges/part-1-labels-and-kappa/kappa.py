"""Challenge 5, part 1: label 30 refund replies yourself, then check yourself against the expert.

Shipped and read, not written:
  agreement_cells(mine, expert)         the four cells of the 2 x 2 table (fail is the positive class)
  disagreement_ids(ids, mine, expert)   the ids where you and the expert differ

Fill the two YOUR TURN gaps:
  cohen_kappa(mine, expert)             chance-corrected agreement; None when chance agreement is 1
  needs_reread(kappa)                   the course rule: below 0.6 you reread the guideline

`mine` and `expert` are lists of "pass" or "fail", one entry per reply, in the same order.

Run the commands, not this file:
  python -m evalkit label --calibration      10 replies, the expert's reason shown after each
  python -m evalkit label --blind            20 replies, no reasons
  python -m evalkit kappa                    your blind labels against the expert's
"""
from __future__ import annotations


def agreement_cells(mine, expert) -> dict:
    """Count the four cells. Fail is the positive class, as in every table of this module."""
    cells = {"both_pass": 0, "mine_pass_expert_fail": 0, "mine_fail_expert_pass": 0, "both_fail": 0}
    for m, e in zip(mine, expert):
        cells[("both_" + m) if m == e else f"mine_{m}_expert_{e}"] += 1
    return cells


def disagreement_ids(ids, mine, expert) -> list:
    return [i for i, m, e in zip(ids, mine, expert) if m != e]


def cohen_kappa(mine, expert):
    """kappa = (po - pe) / (1 - pe). po is the share of replies where you and the expert agree. pe is the agreement expected by chance:
    for each label, your share of that label times the expert's share, added up over both labels.
    If pe is 1 there is nothing to correct (both of you gave every reply the same label): return None, never divide by zero."""
    raise NotImplementedError("YOUR TURN: po, pe, then (po - pe) / (1 - pe); None when pe is 1")


def needs_reread(kappa) -> bool:
    """The course rule: kappa below 0.6 means reread the guideline and the calibration reasons. An undefined kappa (None) also means reread."""
    raise NotImplementedError("YOUR TURN: True when kappa is None or below 0.6")
