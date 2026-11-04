"""Challenge 2, part 1: read your notes back. Nothing here is a gap; the work is the notes file itself.

    python challenges/challenge-2-error-analysis/part-1-open-notes/notes_summary.py

It prints how many of your 30 notes are clean, your timing, and the words you used most. Those repeated words
are the first names for the failure modes you group in 2.6.
"""
from __future__ import annotations

import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit import notes  # noqa: E402

HERE = Path(__file__).resolve().parent
COMMON = set("the a an and or of to in it is was that this for with on as by at not no its from has have but they their your you reply says which".split())


def top_words(rows, n=10):
    words = Counter(w for r in rows for w in re.findall(r"[a-z']+", r["note"].lower()) if w not in COMMON and len(w) > 3)
    return words.most_common(n)


def main():
    rows = notes.read_notes(HERE / "my_notes.jsonl")
    clean = [r for r in rows if not notes.problems(r["note"])]
    print(f"{len(clean)} clean notes of {len(notes.LEARNER_TRACES)} ({len(rows) - len(clean)} flagged)")
    print(notes.timing_line(rows))
    failing = [r for r in clean if not notes.NO_FAILURE.search(r["note"])]
    print(f"notes that name a failure: {len(failing)}; notes that say no failure: {len(clean) - len(failing)}")
    print("words you reused (word, times):", ", ".join(f"{w} {n}" for w, n in top_words(failing)))
    if rows:
        print(f"median seconds {statistics.median(r['seconds'] for r in rows):.0f}")


if __name__ == "__main__":
    main()
