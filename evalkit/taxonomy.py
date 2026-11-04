"""Shipped helpers for 2.6: read `my_taxonomy.yaml`, check it, rank the modes.

The file is a small, plain subset of YAML (see the part README):

    saturation_at: 27
    modes:
      States a fact it cannot support: {weight: 3, example: tr52}
      No failure found: {weight: 0, example: tr02}
    traces:
      tr01: States a fact it cannot support
      tr02: No failure found

`traces:` lists the mode of each trace in the order you read them. `rank_modes` is shipped: the learner reads it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "datasets" / "traces" / "traces.jsonl"
AUTHOR_TAXONOMY = ROOT / "datasets" / "traces" / "author_taxonomy.json"
DEFAULT_FILE = ROOT / "challenges" / "challenge-2-error-analysis" / "part-2-taxonomy-and-criteria" / "my_taxonomy.yaml"
NO_FAILURE = "no failure"


def is_no_failure(mode: str) -> bool:
    return mode.strip().lower().startswith(NO_FAILURE)


def trace_ids() -> list[str]:
    return [json.loads(l)["trace_id"] for l in TRACES.read_text(encoding="utf-8").splitlines() if l.strip()]


def parse_taxonomy(text: str) -> dict:
    """Returns {"saturation_at": int or None, "modes": {name: {"weight": int, "example": str}}, "traces": [(id, mode)]}."""
    out = {"saturation_at": None, "modes": {}, "traces": []}
    section = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith(" "):
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if key == "saturation_at":
                out["saturation_at"] = int(val) if re.fullmatch(r"\d+", val) else None
            else:
                section = key
            continue
        key, _, val = line.strip().partition(":")
        if section == "modes":
            w = re.search(r"weight:\s*(\d+)", val)
            e = re.search(r"example:\s*([^\s,}]+)", val)
            out["modes"][key.strip()] = {"weight": int(w.group(1)) if w else None, "example": e.group(1) if e else None}
        elif section == "traces":
            out["traces"].append((key.strip(), val.strip()))
    return out


def rank_modes(assignments: dict, costs: dict) -> list[dict]:
    """Shipped (2.6). assignments: trace id -> mode name. costs: mode name -> cost weight (1 to 3).
    score = count x cost weight. Highest score first; ties broken by mode name. Both columns are kept in each row,
    so a reader sees that a rare mode with a high weight can outrank a common mode with a low one.
    A mode with no cost (the 'no failure' group) is not ranked."""
    counts: dict = {}
    for mode in assignments.values():
        counts[mode] = counts.get(mode, 0) + 1
    rows = [{"mode": m, "count": n, "weight": costs[m], "score": n * costs[m]} for m, n in counts.items() if m in costs and costs[m]]
    return sorted(rows, key=lambda r: (-r["score"], r["mode"]))


def saturation_position(order: list, assignments: dict) -> int | None:
    """Position (1 based, in the order given) of the trace that first shows the last new failure mode."""
    seen, last = set(), None
    for i, t in enumerate(order, 1):
        m = assignments.get(t)
        if m and not is_no_failure(m) and m not in seen:
            seen.add(m)
            last = i
    return last


def check_taxonomy(tax: dict) -> list[str]:
    """Problems, as plain sentences. Empty list means the check passes."""
    problems = []
    ids = trace_ids()
    modes = tax["modes"]
    if not modes:
        return ["no modes: write the 'modes:' section"]
    listed = [t for t, _ in tax["traces"]]
    missing = [t for t in ids if t not in listed]
    extra = [t for t in listed if t not in ids]
    dup = sorted({t for t in listed if listed.count(t) > 1})
    counted = len(set(listed) & set(ids))
    if counted != len(ids) or dup or extra:
        problems.append(f"counted {counted} of {len(ids)} traces: every trace needs exactly one top mode"
                        + (f" (missing: {', '.join(missing[:8])}{' ...' if len(missing) > 8 else ''})" if missing else "")
                        + (f" (listed twice: {', '.join(dup)})" if dup else "") + (f" (not a trace: {', '.join(extra)})" if extra else ""))
    for t, m in tax["traces"]:
        if m not in modes:
            problems.append(f"{t}: mode '{m}' is not defined under 'modes:'")
    by_mode: dict = {}
    for t, m in tax["traces"]:
        by_mode.setdefault(m, []).append(t)
    for name, spec in modes.items():
        if is_no_failure(name):
            continue
        if spec["weight"] not in (1, 2, 3):
            problems.append(f"{name}: cost weight must be 1, 2 or 3 (got {spec['weight']})")
        if spec["example"] not in by_mode.get(name, []):
            problems.append(f"{name}: the example trace {spec['example']} must be one of the traces in this mode")
    if tax["saturation_at"] is None:
        problems.append("saturation_at is missing: write the position (1 to 60) of the trace where your notes last added a new mode")
    elif not 1 <= tax["saturation_at"] <= len(ids):
        problems.append("saturation_at must be a number from 1 to 60")
    return problems


def author_taxonomy() -> dict:
    return json.loads(AUTHOR_TAXONOMY.read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else DEFAULT_FILE
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        print(f"taxonomy-check: {path.name} is empty or missing. Fill it in (see the part README).")
        return 1
    tax = parse_taxonomy(path.read_text(encoding="utf-8"))
    problems = check_taxonomy(tax)
    if problems:
        print("taxonomy-check: FAILED")
        for p in problems:
            print(f"  - {p}")
        return 1
    costs = {m: s["weight"] for m, s in tax["modes"].items()}
    assignments = dict(tax["traces"])
    rows = rank_modes(assignments, costs)
    print(f"taxonomy-check: OK, {len(assignments)} of {len(trace_ids())} traces counted, {len(rows)} failure modes")
    print("")
    print("| rank | mode | count | cost weight | score (count x weight) |")
    print("|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        print(f"| {i} | {r['mode']} | {r['count']} | {r['weight']} | {r['score']} |")
    nf = sum(1 for m in assignments.values() if is_no_failure(m))
    print(f"\nNo failure found: {nf} traces (counted, not ranked)")
    pos = saturation_position([t for t, _ in tax["traces"]], assignments)
    note = "matches" if pos == tax["saturation_at"] else f"does NOT match (reading order gives {pos})"
    print(f"saturation_at: {tax['saturation_at']} {note}; the author's own reading gave {author_taxonomy()['saturation_at']}")
    return 0
