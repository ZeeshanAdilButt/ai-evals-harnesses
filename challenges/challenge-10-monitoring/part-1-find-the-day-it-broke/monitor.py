"""Challenge 10, part 1: find the day it broke. Somewhere in a recorded week, something broke.

The week is 3,500 tickets over seven days. Judge v3 (the canonical judge, 5.8) graded the reply to every refund ticket and the verdicts
are recorded, so everything here is replay. The shipped commands load the data and call your two functions:

  python -m evalkit monitor --day all                  the week by day, all slices together     -> daily_rates(judged, ["day"])
  python -m evalkit monitor --day 5 --slice language   one day cut by a slice                   -> daily_rates(judged, ["day", "language"])
  python -m evalkit monitor --slice tone               every day cut by tone
  python -m evalkit monitor --canary                   the fixed canary set, one line per day (shipped, no gap)

`judged` is a list of dicts, one per judged refund reply: {"id", "day", "tone", "language", "length", "passed"}. `passed` is the judge's
verdict. The rates you compute are OBSERVED rates: they are what the judge said, and the judge has its own TPR and TNR (chapter 5).

Fill the two YOUR TURN gaps: daily_rates and flag_cells. Decide the numbers in RULE yourself, from what the week looks like.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from evalkit.stats import rate_interval  # noqa: E402,F401  (shipped: the interval of a rate, with the rule of three at the edges)

# Your flagging rule. min_n: a cell with fewer judged replies is never flagged (10.5: small cells are noisy).
# min_drop: the observed pass rate must be at least this far (in rate, 0.10 = 10 points) below the slice's usual rate.
RULE = {"min_n": 20, "min_drop": 0.10}


def daily_rates(judged, group_by):
    """Group the judged replies by the fields in `group_by` (for example ["day"] or ["day", "language"]) and describe each cell.
    Return a list of dicts sorted by cell: {"cell": a tuple of the group values, "n": replies in the cell, "passes": how many passed,
    "rate": passes / n (observed pass rate), "lo": low end, "hi": high end} where (lo, hi) = rate_interval(passes, n)."""
    raise NotImplementedError("YOUR TURN: count n and passes per cell, then rate and rate_interval(passes, n)")


def flag_cells(table, baseline_days, rule):
    """table: the rows of daily_rates(judged, ["day", S]) for one slice axis S, so row["cell"] is (day, value of S).
    baseline_days: the days that count as usual (for example [1, 2, 3, 4]). rule: a dict like RULE.
    For each value of S, the usual rate is the pooled pass rate of that value over the baseline days (all passes over all replies).
    Flag a cell (a day outside the baseline days) when it has at least rule["min_n"] replies, its observed rate is at least rule["min_drop"]
    below the usual rate, and the top of its interval (row["hi"]) is below the usual rate: the drop is bigger than the noise.
    Return the flagged cells as a sorted list of (day, value)."""
    raise NotImplementedError("YOUR TURN: usual rate per slice value from the baseline days, then the three tests on every other cell")
