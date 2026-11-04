"""The open-note tool (2.5): `python -m evalkit notes [--check]`. No model is called; the traces are files.

You read one trace at a time and type one note. The tool times you and flags a note that is
under 8 words or that names no failure. `--check` reads the saved file and reports every problem.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "datasets" / "traces" / "traces.jsonl"
DEFAULT_FILE = ROOT / "challenges" / "challenge-2-error-analysis" / "part-1-open-notes" / "my_notes.jsonl"
MIN_WORDS = 8
MIN_MEDIAN_SECONDS = 25
LEARNER_TRACES = [f"tr{i:02d}" for i in range(1, 31)]  # the other 30 carry the author's notes (opened in 2.6)

# A note names a failure when it says "no failure found", quotes the reply or the ticket, cites a number,
# or uses a word that points at something the reply did or claimed.
NO_FAILURE = re.compile(r"\bno failure\b|\bnothing wrong\b|\bno problem found\b", re.I)
FAILURE_WORDS = re.compile(
    r"\b(says|said|states|stated|claims|claimed|promises|promised|invents|invented|offers|offered|opens|opened|switches|switched|"
    r"adds|added|applies|applied|ignores|ignored|misses|missed|wrong|unsupported|cannot|can't|never|without|writes|wrote|tells|told|"
    r"assumes|repeats|blames|refuses|asks|asked|gives|gave|mentions|calls|confirms|guesses|contradicts|leaves out|fails)\b", re.I)
QUOTE_OR_NUMBER = re.compile(r"['\"‘’“”]\w|\d|\$")


def words(note: str) -> int:
    return len(re.findall(r"\S+", note))


def problems(note: str) -> list[str]:
    """Why a note is flagged. An empty list means the note is clean."""
    out = []
    if words(note) < MIN_WORDS:
        out.append(f"under {MIN_WORDS} words ({words(note)})")
    if not (NO_FAILURE.search(note) or FAILURE_WORDS.search(note) or QUOTE_OR_NUMBER.search(note)):
        out.append("names no failure")
    return out


def load_traces() -> dict:
    return {r["trace_id"]: r for r in map(json.loads, TRACES.read_text(encoding="utf-8").splitlines()) if r}


def read_notes(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def timing_line(rows: list[dict]) -> str:
    if not rows:
        return "timing: no notes yet"
    med = statistics.median(r["seconds"] for r in rows)
    total = sum(r["seconds"] for r in rows)
    line = f"timing: median {med:.0f} s per trace over {len(rows)} traces, {total / 60:.1f} minutes in all"
    if med < MIN_MEDIAN_SECONDS:
        fastest = [r["trace_id"] for r in sorted(rows, key=lambda r: r["seconds"])[:3]]
        line += f"\nWARNING: a median under {MIN_MEDIAN_SECONDS} s means you are skimming. Reread {', '.join(fastest)} and rewrite their notes."
    return line


def check(path: Path) -> int:
    rows = read_notes(path)
    bad = 0
    seen = set()
    for r in rows:
        why = problems(r["note"])
        if r["trace_id"] in seen:
            why.append("listed twice")
        seen.add(r["trace_id"])
        if r["trace_id"] not in LEARNER_TRACES:
            why.append("not one of your 30 traces (tr01 to tr30)")
        if why:
            bad += 1
            print(f"flagged {r['trace_id']}: {'; '.join(why)}")
    missing = [t for t in LEARNER_TRACES if t not in seen]
    if missing:
        print(f"missing {len(missing)} of {len(LEARNER_TRACES)} traces: {', '.join(missing[:6])}{' ...' if len(missing) > 6 else ''}")
    clean = len(rows) - bad
    print(f"notes --check: {clean} clean of {len(LEARNER_TRACES)}, {bad} flagged, {len(missing)} missing")
    print(timing_line(rows))
    return 0 if not bad and not missing else 1


def run(path: Path) -> int:
    traces = load_traces()
    rows = read_notes(path)
    done = {r["trace_id"] for r in rows if not problems(r["note"])}
    todo = [t for t in LEARNER_TRACES if t not in done]
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = [r for r in rows if r["trace_id"] in done]
    for t in todo:
        tr = traces[t]
        n = LEARNER_TRACES.index(t) + 1
        print(f"\n=== Trace {n} of {len(LEARNER_TRACES)} ({t}) ===\nTICKET:\n{tr['ticket']}\n\nREPLY:\n{tr['reply']}\n")
        started = time.monotonic()
        while True:
            try:
                note = input("note> ").strip()
            except EOFError:
                print("\n(input ended; your saved notes are kept. Run notes again to continue.)")
                path.write_text("".join(json.dumps(r) + "\n" for r in kept), encoding="utf-8")
                return 1
            why = problems(note)
            if not why:
                break
            print(f"flagged: {'; '.join(why)}. Write what the reply did or claimed that it should not have, or 'No failure found. ...' and why.")
        seconds = round(time.monotonic() - started, 1)
        kept.append({"trace_id": t, "note": note, "seconds": seconds})
        print(f"accepted ({seconds:.0f} s)")
        path.write_text("".join(json.dumps(r) + "\n" for r in kept), encoding="utf-8")
    print("\n" + timing_line(kept))
    return 0


def main(argv: list[str]) -> int:
    args = list(argv)
    path = DEFAULT_FILE
    if "--file" in args:
        i = args.index("--file")
        path = Path(args[i + 1])
        del args[i:i + 2]
    if "--check" in args:
        return check(path)
    return run(path)
