"""`python -m evalkit dataset select|scrub|dedupe|split|freeze|compare` (3.7, and `freeze` again in 10.7).

Shipped and finished. It calls the five functions you write in
challenges/challenge-3-dataset/part-1-dataset-v1/build_dataset.py and keeps the files of each step in datasets/mine/.
It never records a case and never calls a model: every pool ticket is already recorded for A and B.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tomllib
from pathlib import Path

from evalkit.neardup import group_near_duplicates, pairs_at_threshold
from evalkit.scrub import scrub_text

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "datasets" / "pool" / "tickets.jsonl"
CANON = ROOT / "datasets" / "canonical" / "v1"
MINE = ROOT / "datasets" / "mine"
PART = ROOT / "challenges" / "challenge-3-dataset" / "part-1-dataset-v1"
DEFAULT_DIMS = PART / "my_dimensions.toml"
KNOWN_DIMS = ("category", "urgent", "tone", "language", "length", "source", "easy")
THIN = 10  # a slice with fewer cases than this is thin


def read_jsonl(path: Path) -> list:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows).encode("utf-8"))


def load_learner(script: Path = PART / "build_dataset.py"):
    spec = importlib.util.spec_from_file_location("learner_build_dataset", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_dims(path: Path) -> dict:
    cfg = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    cfg.setdefault("filters", {})
    cfg.setdefault("slices", {})
    cfg.setdefault("per_mix", 2)
    cfg.setdefault("heldout_share", 0.25)
    cfg.setdefault("seed", 7)
    cfg.setdefault("dedupe_threshold", 0.8)
    bad = [d for d in cfg.get("dimensions", []) if d not in KNOWN_DIMS]
    if not cfg.get("dimensions") or bad:
        raise SystemExit(f"dimensions: choose from {', '.join(KNOWN_DIMS)}" + (f" (not: {', '.join(bad)})" if bad else ""))
    return cfg


def apply_filters(pool: list, filters: dict) -> list:
    def ok(row):
        return all(row[k] in (v if isinstance(v, list) else [v]) for k, v in filters.items())
    return [r for r in pool if ok(r)]


def flat(case: dict) -> dict:
    """A canonical case (nested dims) as a flat row, so the same slice rules apply to both datasets."""
    if "dims" not in case:
        return case
    return {"id": case["id"], "text": case["text"], "category": case["expected"]["category"], "urgent": case["expected"]["urgent"],
            **case["dims"], "split": case.get("split")}


def to_case(row: dict) -> dict:
    """The frozen shape: the same as canonical dataset v1, plus the slices you tagged."""
    return {"id": row["id"], "split": row["split"], "text": row["text"],
            "expected": {"category": row["category"], "urgent": row["urgent"]},
            "dims": {k: row[k] for k in ("tone", "language", "length", "source", "easy")}, "slices": row.get("slices", [])}


def step_select(dims_path: Path) -> list:
    cfg = load_dims(dims_path)
    MINE.mkdir(parents=True, exist_ok=True)
    (MINE / "state.json").write_text(json.dumps({"dims": str(Path(dims_path).resolve())}), encoding="utf-8")
    pool = apply_filters(read_jsonl(POOL), cfg["filters"])
    mod = load_learner()
    chosen = mod.select_cases(pool, cfg["dimensions"], cfg["per_mix"])
    write_jsonl(MINE / "selected.jsonl", chosen)
    avail: dict = {}
    for r in pool:
        avail.setdefault(tuple(r[d] for d in cfg["dimensions"]), 0)
        avail[tuple(r[d] for d in cfg["dimensions"])] += 1
    thin = {k: n for k, n in avail.items() if n < cfg["per_mix"]}
    print(f"pool: {len(pool)} tickets after filters {cfg['filters'] or '(none)'}")
    print(f"mixes over {', '.join(cfg['dimensions'])}: {len(avail)} filled, per_mix {cfg['per_mix']}")
    print(f"selected: {len(chosen)} tickets -> {(MINE / 'selected.jsonl').relative_to(ROOT).as_posix()}")
    if thin:
        print(f"{len(thin)} mixes have fewer than {cfg['per_mix']} tickets in the pool, so they give all they have (the tool never records new cases):")
        for k, n in sorted(thin.items(), key=lambda kv: kv[1])[:8]:
            print(f"  {' / '.join(map(str, k))}: {n}")
        print("to fill them, drop one dimension from `dimensions` or lower per_mix.")
    return chosen


def step_scrub() -> list:
    rows = read_jsonl(MINE / "selected.jsonl")
    bad, out = [], []
    for r in rows:
        s = scrub_text(r["raw_text"])
        if s != r["text"]:
            bad.append(r["id"])
        out.append({k: v for k, v in r.items() if k != "raw_text"} | {"text": s})
    write_jsonl(MINE / "scrubbed.jsonl", out)
    with_pii = sum(1 for r in rows if r["raw_text"] != r["text"])
    print(f"scrubbed {len(rows)} tickets ({with_pii} had an email or phone number); raw_text is not kept in the next file")
    if bad:
        print(f"MISMATCH: {len(bad)} tickets scrub to something other than the pool's text: {', '.join(bad[:8])}")
        print("A recording was made on the pool's text, so a different text would miss in replay. Stop and tell your mentor.")
        sys.exit(1)
    print(f"check: all {len(rows)} scrubbed texts equal the pool's text, so every case is already recorded for A and B")
    return out


def step_dedupe() -> list:
    cfg = load_dims(Path(json.loads((MINE / "state.json").read_text(encoding="utf-8"))["dims"]))
    rows = read_jsonl(MINE / "scrubbed.jsonl")
    kept = load_learner().drop_near_duplicates(rows, cfg["dedupe_threshold"])
    write_jsonl(MINE / "deduped.jsonl", kept)
    kept_ids = {r["id"] for r in kept}
    pairs = pairs_at_threshold(rows, cfg["dedupe_threshold"])
    print(f"near-duplicate threshold {cfg['dedupe_threshold']} (Jaccard on lowercase word sets): {len(pairs)} pairs at or above it")
    for a, b, o in pairs:
        print(f"  {a} ~ {b} overlap {o}")
    dropped = [r["id"] for r in rows if r["id"] not in kept_ids]
    print(f"kept {len(kept)} of {len(rows)}; dropped {len(dropped)}" + (f": {', '.join(dropped)}" if dropped else ""))
    return kept


def step_split() -> list:
    state = json.loads((MINE / "state.json").read_text(encoding="utf-8"))
    cfg = load_dims(Path(state["dims"]))
    mod = load_learner()
    rows = read_jsonl(MINE / "deduped.jsonl")
    tagged = mod.tag_slices(rows, cfg["slices"])
    groups = group_near_duplicates(tagged, cfg["dedupe_threshold"])
    out = mod.split_cases(groups, cfg["heldout_share"], cfg["seed"])
    write_jsonl(MINE / "split.jsonl", out)
    dev = sum(1 for r in out if r["split"] == "dev")
    print(f"split: dev {dev}, held-out {len(out) - dev} (held-out share asked {cfg['heldout_share']}, seed {cfg['seed']})")
    print("")
    print(slice_table(out, cfg["slices"]))
    return out


def slice_table(rows: list, rules: dict) -> str:
    lines = ["| slice | n | thin |", "|---|---|---|"]
    for name in rules:
        n = sum(1 for r in rows if name in r.get("slices", []))
        lines.append(f"| {name} | {n} | {'thin (n under ' + str(THIN) + ')' if n < THIN else ''} |")
    return "\n".join(lines)


def trace_case(row: dict) -> dict:
    """A selected traffic trace in the shape of a canonical v2 addition."""
    return {"id": row["id"], "split": "v2_addition", "text": row["text"], "expected": row["expected"],
            "dims": {"tone": row["tone"], "language": row["language"], "length": row["length"], "source": "traffic", "easy": False}}


def step_freeze(name: str, traces: bool = False) -> dict:
    """Freeze the pipeline's split (3.7), or with --traces (the default for a name ending in v2) the traces that
    `select-traces` chose (10.7): your v2 additions."""
    if traces:
        sel = MINE / "trace_selection.jsonl"
        if not sel.exists():
            raise FileNotFoundError(2, "missing", str(sel))
        cases = [trace_case(r) for r in read_jsonl(sel)]
    else:
        rows = read_jsonl(MINE / "split.jsonl")
        cases = [to_case(r) for r in rows]
    frozen = load_learner().freeze(cases, name)
    out = MINE / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "cases.jsonl").write_bytes(frozen["body"].encode("utf-8"))  # LF on every system, so the file hashes to the hash printed
    (out / "HASH").write_bytes((frozen["hash"] + "\n").encode("utf-8"))
    print(f"frozen {frozen['n']} cases as {name} -> {(out / 'cases.jsonl').relative_to(ROOT).as_posix()}")
    print(f"hash: {frozen['hash']}")
    return frozen


def step_compare_v2(name: str) -> dict:
    """Your frozen v2 additions against canonical dataset v2's 40 additions: overlap, missed, extra."""
    mine = {c["id"]: c for c in read_jsonl(MINE / name / "cases.jsonl")}
    canon = {c["id"]: c for c in read_jsonl(ROOT / "datasets/canonical/v2/additions.jsonl")}
    both, missed, extra = sorted(set(mine) & set(canon)), sorted(set(canon) - set(mine)), sorted(set(mine) - set(canon))
    mh = (MINE / name / "HASH").read_text(encoding="utf-8").strip()
    print(f"yours:     {len(mine)} traces, hash {mh[:12]}")
    print(f"canonical: {len(canon)} v2 additions (refund traces from the broken slice)")
    print(f"in both: {len(both)}; you missed: {len(missed)}; extra in yours: {len(extra)}")
    if missed:
        print(f"  missed (first 8): {', '.join(missed[:8])}")
    if extra:
        print(f"  extra (first 8): {', '.join(extra[:8])}")
    return {"mine": len(mine), "canon": len(canon), "both": len(both), "missed": len(missed), "extra": len(extra), "hash": mh}


def step_compare(name: str) -> dict:
    if name.endswith("v2"):
        return step_compare_v2(name)
    state = json.loads((MINE / "state.json").read_text(encoding="utf-8"))
    cfg = load_dims(Path(state["dims"]))
    mine = read_jsonl(MINE / name / "cases.jsonl")
    canon = read_jsonl(CANON / "cases.jsonl")
    mh = (MINE / name / "HASH").read_text(encoding="utf-8").strip()
    ch = (CANON / "HASH").read_text(encoding="utf-8").strip()
    mi, ci = {c["id"] for c in mine}, {c["id"] for c in canon}
    only_mine, only_canon, shared = sorted(mi - ci), sorted(ci - mi), sorted(mi & ci)
    print(f"yours:     {len(mine)} cases, hash {mh[:12]}")
    print(f"canonical: {len(canon)} cases, hash {ch[:12]}")
    print(f"hashes {'match' if mh == ch else 'differ'}")
    print(f"in both: {len(shared)}; only in yours: {len(only_mine)}; only in canonical: {len(only_canon)}")
    if only_mine:
        print(f"  only in yours (first 8): {', '.join(only_mine[:8])}")
    if only_canon:
        print(f"  only in canonical (first 8): {', '.join(only_canon[:8])}")
    mf = [flat(c) for c in mine]
    mod = load_learner()
    cf = mod.tag_slices([flat(c) for c in canon], cfg["slices"])
    mf = mod.tag_slices(mf, cfg["slices"])
    print("\n| slice | yours n | canonical n | note |")
    print("|---|---|---|---|")
    rows = []
    for s in cfg["slices"]:
        a = sum(1 for r in mf if s in r["slices"])
        b = sum(1 for r in cf if s in r["slices"])
        note = "thin in yours" if a < THIN else ("thin in canonical" if b < THIN else "")
        print(f"| {s} | {a} | {b} | {note} |")
        rows.append((s, a, b))
    dev = sum(1 for c in mine if c["split"] == "dev")
    print(f"\nsplit: yours dev {dev} / held-out {len(mine) - dev}; canonical dev {sum(1 for c in canon if c['split'] == 'dev')} / held-out {sum(1 for c in canon if c['split'] == 'heldout')}")
    return {"mine": len(mine), "canon": len(canon), "only_mine": len(only_mine), "only_canon": len(only_canon), "shared": len(shared),
            "slices": rows, "hash": mh}


def run_all(dims_path: Path, script: Path, name: str = "v1") -> None:
    step_select(dims_path)
    step_scrub()
    step_dedupe()
    step_split()
    step_freeze(name)
    step_compare(name)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python -m evalkit dataset select --dims FILE | scrub | dedupe | split | freeze --name N | compare [--name N]")
        return 2
    cmd, rest = argv[0], argv[1:]

    def opt(flag, default):
        return rest[rest.index(flag) + 1] if flag in rest else default

    try:
        if cmd == "select":
            step_select(Path(opt("--dims", DEFAULT_DIMS)))
        elif cmd == "scrub":
            step_scrub()
        elif cmd == "dedupe":
            step_dedupe()
        elif cmd == "split":
            step_split()
        elif cmd == "freeze":
            step_freeze(opt("--name", "v1"), traces="--traces" in rest or opt("--name", "v1").endswith("v2"))
        elif cmd == "compare":
            step_compare(opt("--name", "v1"))
        else:
            print(f"dataset: unknown step {cmd}")
            return 2
    except NotImplementedError as err:
        print(f"dataset {cmd}: {err}")
        return 1
    except FileNotFoundError as err:
        print(f"dataset {cmd}: the previous step has not run yet ({Path(err.filename).name} is missing)")
        return 1
    return 0
