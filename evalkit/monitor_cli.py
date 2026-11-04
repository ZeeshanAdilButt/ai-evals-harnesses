"""Module 10 commands: monitor, monitor --canary, select-traces (shipped, finished). Replay only.

The pieces the learner writes live in the challenge 10 part:
  part-1-find-the-day-it-broke/monitor.py   daily_rates, flag_cells
  part-1-find-the-day-it-broke/rule.py      select_rule
The judged sample is judge v3 on refund replies, recorded; a verdict is found by request key. A reply or verdict that is not
recorded yet is counted and printed, never guessed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from evalkit import traffic
from evalkit.judges_cli import load_module

ROOT = traffic.ROOT
P1 = ROOT / "challenges" / "challenge-10-monitoring" / "part-1-find-the-day-it-broke"
MINE = ROOT / "datasets" / "mine"
SELECTION = MINE / "trace_selection.jsonl"
AXES = ("tone", "language", "length")


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def table_text(rows: list, cols: list) -> str:
    head = "| " + " | ".join(cols + ["n", "observed pass rate", "95% interval"]) + " |"
    lines = [head, "|" + "---|" * (len(cols) + 3)]
    for r in rows:
        cell = list(r["cell"]) if isinstance(r["cell"], (list, tuple)) else [r["cell"]]
        lines.append("| " + " | ".join(str(c) for c in cell) + f" | {r['n']} | {pct(r['rate'])} | ({pct(r['lo'])}, {pct(r['hi'])}) |")
    return "\n".join(lines)


def notice(rows_all: list) -> int:
    gone = traffic.missing(rows_all)
    if gone:
        print(f"not recorded yet: {len(gone)} of {sum(r['category'] == 'refund' for r in rows_all)} refund traces have no judge verdict "
              "(the author records them with tools/record_judge.py); the table below counts only the judged ones")
    return len(gone)


def cmd_monitor(argv: list[str]) -> int:
    opt = lambda f, d=None: argv[argv.index(f) + 1] if f in argv else d  # noqa: E731
    if "--canary" in argv:
        return canary()
    day, slice_ = opt("--day", "all"), opt("--slice")
    if slice_ is not None and slice_ not in AXES:
        print(f"unknown slice {slice_!r}: choose one of {', '.join(AXES)}")
        return 2
    rows_all = traffic.week()
    notice(rows_all)
    judged = traffic.judged(rows_all)
    if day != "all":
        judged = [r for r in judged if r["day"] == int(day)]
    group = ["day"] + ([slice_] if slice_ else [])
    mod = load_module(P1 / "monitor.py", "learner_monitor")
    try:
        table = mod.daily_rates(judged, group)
    except NotImplementedError as err:
        print(err)
        return 1
    what = "all slices together" if not slice_ else f"by {slice_}"
    print(f"judge v3 on refund replies, {'the week' if day == 'all' else 'day ' + day}, {what}. Rates are observed (what the judge said), "
          "fail is the judge's positive class; the interval is the bootstrap interval of the pass rate (rule of three at 0 or all).")
    print(table_text(table, group))
    return 0


def canary() -> int:
    rows = traffic.canary_week()
    gone = [r for r in rows if r["verdict"] is None]
    if gone:
        print(f"not recorded yet: {len(gone)} of {len(rows)} canary verdicts (the author records them with tools/record_judge.py); days with a missing verdict are marked")
    out = {}
    for d in range(1, 8):
        day = [r for r in rows if r["day"] == d and r["verdict"] is not None]
        n_all = sum(r["day"] == d for r in rows)
        p = sum(r["verdict"] == "pass" for r in day)
        out[d] = (p, len(day), n_all)
        rate = f"{pct(p / len(day))} ({p} of {len(day)} judged replies passed)" if day else "no verdicts"
        print(f"day {d}: canary pass rate {rate}, set size {n_all} refund replies" + ("" if len(day) == n_all else "  (incomplete)"))
    rates = {d: p / n for d, (p, n, _) in out.items() if n}
    if len(rates) == 7 and not gone:
        usual = sum(rates[d] for d in range(1, 5)) / 4
        low = min(rates, key=lambda d: (rates[d], d))
        if rates[low] <= usual - 0.10:
            week = [r for r in traffic.week() if r["day"] == low and r["verdict"] is not None]
            overall = sum(r["verdict"] == "pass" for r in week) / len(week) if week else None
            print(f"the canary fell on day {low} ({pct(rates[low])} against {pct(usual)} on days 1 to 4)"
                  + (f"; the traffic-sampled overall pass rate that day was {pct(overall)}" if overall is not None else ""))
        else:
            print("the canary did not fall by 10 points or more on any day")
    return 0


def cmd_select_traces(argv: list[str]) -> int:
    if "--rule" not in argv:
        print("usage: select-traces --rule FILE")
        return 2
    path = Path(argv[argv.index("--rule") + 1])
    rows_all = traffic.week(refund_only=False)
    notice([r for r in rows_all if r["category"] == "refund"])
    try:
        rule = load_module(path if path.is_absolute() else ROOT / path, "learner_rule").select_rule
        chosen = [r for r in rows_all if rule(dict(r))]
    except NotImplementedError as err:
        print(err)
        return 1
    MINE.mkdir(parents=True, exist_ok=True)
    keep = ("id", "day", "tone", "language", "length", "category", "urgent", "text", "expected", "verdict")
    SELECTION.write_text("".join(json.dumps({k: r[k] for k in keep}, ensure_ascii=False, sort_keys=True) + "\n" for r in chosen), encoding="utf-8")
    print(f"selected {len(chosen)} of {len(rows_all)} traces; written to {SELECTION.relative_to(ROOT).as_posix()}")
    from collections import Counter
    print("by day: " + ", ".join(f"d{d} {n}" for d, n in sorted(Counter(r['day'] for r in chosen).items())))
    print("by language: " + ", ".join(f"{k} {n}" for k, n in sorted(Counter(r['language'] for r in chosen).items())))
    print("by category: " + ", ".join(f"{k} {n}" for k, n in sorted(Counter(r['category'] for r in chosen).items())))
    print("next: python -m evalkit dataset freeze --name my-v2")
    return 0


def monitor_main(argv):
    return cmd_monitor(argv)


def select_traces_main(argv):
    return cmd_select_traces(argv)


if __name__ == "__main__":
    sys.exit(cmd_monitor(sys.argv[1:]))
