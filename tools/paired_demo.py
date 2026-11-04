"""Constructed demo for chapter 7.6. Not a run of the FreshMarket model."""
import argparse, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evalkit import stats

LISTS = {
    1: [(0.0, 84), (0.2, 14), (0.4, 6), (0.6, 4), (-0.2, 8), (-0.4, 4)],
    2: [(0.0, 92), (0.2, 10), (0.4, 4), (0.6, 2), (-0.2, 8), (-0.4, 4)],
}
def pts(x): return f"{100 * x:+.1f}"
ap = argparse.ArgumentParser()
ap.add_argument("--list", type=int, required=True)
ap.add_argument("--draw", type=int, default=0)
ap.add_argument("--interval", action="store_true")
a = ap.parse_args()
spec = LISTS[a.list]
diffs = [v for v, c in spec for _ in range(c)]
n = len(diffs)
if not (a.draw or a.interval):
    print(f"list {a.list} (constructed): {n} cases, B mean minus A mean per case")
    for v, c in spec: print(f"{v:+.1f}: {c} cases")
    print(f"mean difference: {pts(stats.mean(diffs))} points")
if a.draw:
    rng = random.Random(7)
    for i in range(1, a.draw + 1):
        m = stats.mean([diffs[rng.randrange(n)] for _ in range(n)])
        print(f"resample {i}: mean difference {pts(m)} points")
if a.interval:
    m, (lo, hi) = stats.paired_bootstrap(diffs)
    print("10,000 resamples, seed 7")
    print(f"mean difference: {pts(m)} points")
    print(f"2.5th percentile: {pts(lo)} points")
    print(f"97.5th percentile: {pts(hi)} points")
    print("verdict: " + stats.verdict((lo, hi)))
