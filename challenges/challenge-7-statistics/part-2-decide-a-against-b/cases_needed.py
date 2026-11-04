"""Chapter 7.7's formula on the recorded A and B. It only reads the recordings."""
import sys
from math import ceil
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE))

import decide

diffs = decide.case_differences(decide.triage_trials("A"), decide.triage_trials("B"))
n = len(diffs)
changed = sum(1 for d in diffs if abs(d) > 1e-9)
q = changed / n
delta = sum(diffs) / n
needed = ceil(max(7.84 * (q - delta ** 2) / delta ** 2, 6 / q))
print(f"{changed} of {n} cases differ: q = {100 * q:.1f}%")
print(f"recorded difference: {100 * delta:.1f} points")
print(f"cases needed for 80% power: {needed}")
