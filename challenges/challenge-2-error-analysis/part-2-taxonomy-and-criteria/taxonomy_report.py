"""Challenge 2, part 2: read the shipped rank_modes, run it on your taxonomy, and set it beside the author's.

Nothing here is a gap. Your work is my_taxonomy.yaml and criteria/v1.md.

    python challenges/challenge-2-error-analysis/part-2-taxonomy-and-criteria/taxonomy_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit import taxonomy  # noqa: E402

HERE = Path(__file__).resolve().parent


def main():
    tax = taxonomy.parse_taxonomy((HERE / "my_taxonomy.yaml").read_text(encoding="utf-8"))
    problems = taxonomy.check_taxonomy(tax)
    if problems:
        print("fix these first (python -m evalkit taxonomy-check):")
        print("\n".join(f"  - {p}" for p in problems))
        return
    assignments = dict(tax["traces"])
    costs = {m: s["weight"] for m, s in tax["modes"].items()}
    mine = taxonomy.rank_modes(assignments, costs)
    author = taxonomy.author_taxonomy()
    print("your ranking (count x cost weight):")
    for r in mine:
        print(f"  {r['mode']}: {r['count']} x {r['weight']} = {r['score']}")
    print("the author's ranking:")
    for r in author["ranking"]:
        print(f"  {r['name']}: {r['count']} x {r['cost_weight']} = {r['score']}")
    pos = taxonomy.saturation_position([t for t, _ in tax["traces"]], assignments)
    print(f"saturation: yours {tax['saturation_at']} (reading order gives {pos}); the author's {author['saturation_at']}")


if __name__ == "__main__":
    main()
