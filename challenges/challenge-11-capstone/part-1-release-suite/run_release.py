"""Challenge 11, part 1: run the release suite on the candidate with the things you built, once.

    python challenges/challenge-11-capstone/part-1-release-suite/run_release.py [--judge ID] [--out DIR]

Reads release_config.toml (the gaps are there: your graders, your gate, your judge, your runner, the slices), runs variant A and the
candidate on the release suite (canonical dataset v2 for triage and reply, the 40 refund tasks) in replay, runs your gate on the candidate
against A, joins the judge's recorded verdicts on the 72 refund replies, and writes summary.json with every number the report needs.

This glue is shipped. It calls no model. A judge verdict that is not recorded yet is reported as such and left out; nothing is guessed.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from evalkit import capstone, engine, runner_reference, stats  # noqa: E402
from evalkit.suites import read_jsonl  # noqa: E402

CONFIG = HERE / "release_config.toml"
SUMMARY = HERE / "summary.json"


def load_config(path: Path = CONFIG) -> dict:
    cfg = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    for table, keys in (("graders", ("triage", "reply", "agent")), ("release", ("gate", "judge", "runner", "slices"))):
        if table not in cfg or any(k not in cfg[table] for k in keys):
            raise SystemExit(f"release_config.toml is not filled in: [{table}] needs {', '.join(keys)}")
    if cfg["release"]["runner"] not in ("learner", "reference"):
        raise SystemExit('release_config.toml: runner must be "learner" or "reference"')
    return cfg


def import_file(path, name):
    p = ROOT / path
    spec = importlib.util.spec_from_file_location(name, p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def grader_overrides(cfg: dict) -> dict:
    """Adapters from your functions to the names the suite uses. Triage and reply graders take (output, case); agent graders (trial, task)."""
    from evalkit.graders import reply as reply_graders
    tri, rep, agent = (import_file(cfg["graders"][k], f"learner_{k}_graders") for k in ("triage", "reply", "agent"))
    return {
        "schema": lambda output, case: tri.grade_triage_schema(output),
        "match": lambda output, case: tri.grade_triage_match(output, case["expected"]),
        "reply_facts": lambda output, case: reply_graders.grade_reply_facts(
            output, reply_graders.all_checks()[case["id"]], contains=rep.grade_reply_contains, days=rep.grade_reply_refund_days),
        "agent_trajectory": lambda trial, task: bool(agent.grade_trajectory(trial, task)["pass"]),
    }


def pick_impl(cfg: dict):
    if cfg["release"]["runner"] == "reference":
        return runner_reference
    from evalkit.runner_learner import load_impl
    return load_impl()


def rate(x: float) -> float:
    return round(x, 4)


def case_means(records: list, feature: str) -> dict:
    acc: dict = {}
    for r in records:
        if r["feature"] == feature:
            acc.setdefault(r["case_id"], []).append(1.0 if r.get("passed") else 0.0)
    return {k: sum(v) / len(v) for k, v in acc.items()}


def paired(a: dict, b: dict, ids=None) -> dict:
    ids = sorted(ids if ids is not None else set(a) & set(b))
    diffs = [b[i] - a[i] for i in ids]
    mean, (lo, hi) = stats.paired_bootstrap(diffs)
    return {"n": len(ids), "A": rate(sum(a[i] for i in ids) / len(ids)), "candidate": rate(sum(b[i] for i in ids) / len(ids)),
            "diff": rate(mean), "lo": rate(lo), "hi": rate(hi), "verdict": stats.verdict((lo, hi))}


def slice_table(feature: str, a: dict, b: dict, slices: list, cases: dict) -> list:
    rows = []
    for axis in slices:
        values = sorted({(c["expected"]["category"] if axis == "category" else c["dims"][axis]) for c in cases.values()})
        for v in values:
            ids = [i for i in a if i in b and i in cases and (cases[i]["expected"]["category"] if axis == "category" else cases[i]["dims"][axis]) == v]
            if ids:
                rows.append({"slice": f"{axis}={v}", **paired(a, b, ids)})
    return rows


def pass_hat(records: list, k: int) -> float:
    by: dict = {}
    for r in records:
        if r["feature"] == "agent":
            by.setdefault(r["case_id"], []).append(bool(r.get("passed")))
    return sum(stats.pass_hat_k(sum(p), len(p), k) for p in by.values()) / len(by)


def trials_passed(records: list, feature: str, case: str) -> int:
    return sum(bool(r.get("passed")) for r in records if r["feature"] == feature and r["case_id"] == case)


def build_summary(cfg: dict, runs: dict, judge: str, gate_mod) -> dict:
    a, c = read_jsonl(runs["A"] / "trials.jsonl"), read_jsonl(runs["candidate"] / "trials.jsonl")
    cases = {x["id"]: x for x in read_jsonl(ROOT / "datasets/canonical/v2/cases.jsonl")}
    gcfg = gate_mod.load_config()
    lines, code = gate_mod.gate(c, a, gcfg)
    q = gate_mod.quarantined_cases(a)
    na, nc = gate_mod.budget_numbers(gate_mod.Run(a, q)), gate_mod.budget_numbers(gate_mod.Run(c, q))
    out = {"dataset_v2_hash": (ROOT / "datasets/canonical/v2/HASH").read_text(encoding="utf-8").strip(), "judge": judge,
           "runner": cfg["release"]["runner"], "release_suite_trials": 5,
           "run_ids": {"A": runs["A"].name, "candidate": runs["candidate"].name}}
    for feature in ("triage", "reply"):
        ma, mc = case_means(a, feature), case_means(c, feature)
        out[feature] = paired(ma, mc)
        out[f"{feature}_slices"] = slice_table(feature, ma, mc, cfg["release"]["slices"], cases)
    weak = min((r for r in out["reply_slices"] if r["n"] >= 20), key=lambda r: (r["diff"], r["slice"]))
    out["reply_weak_slice"] = weak
    out["agent"] = {"tasks": 40, "trials": 5, **{f"pass{k}_{v}": rate(pass_hat(recs, k)) for k in (1, 4) for v, recs in (("A", a), ("candidate", c))}}
    must = sorted({(r["feature"], r["case_id"]) for r in a + c if r.get("must_pass")})
    rows = [{"feature": f, "case": i, "A": trials_passed(a, f, i), "candidate": trials_passed(c, f, i), "trials": 5} for f, i in must]
    failing = [r for r in rows if r["candidate"] < 5]
    agent_fail = next((r for r in failing if r["feature"] == "agent"), failing[0] if failing else None)
    out["mustpass"] = {"n": len(rows), "cases": rows, "fail_task": agent_fail["case"] if agent_fail else None,
                       "fail_trials": agent_fail["candidate"] if agent_fail else None, "failing_cases": [r["case"] for r in failing]}
    out["cost"] = {"cost1k_A": rate(na["cost_per_1k"]), "cost1k_candidate": rate(nc["cost_per_1k"]), "p95_A_ms": na["p95_ms"], "p95_candidate_ms": nc["p95_ms"],
                   "budget_cost_per_1k": gcfg["budget"]["cost_per_1k"], "budget_p95_ms": gcfg["budget"]["p95_ms"]}
    block = [t for lv, t in lines if lv == "BLOCK"]
    out["gate"] = {"exit": code, "block_reason": block[0] if block else None, "block_lines": block,
                   "lines": [f"{lv} {t}" for lv, t in lines]}
    j = capstone.judged(judge)
    out["judge_result"] = {"judge": judge, "status": capstone.status_lines(judge), "recorded": all(not d["missing"] for d in j.values()),
                           "judged_n": min(len(d["case_rates"]) for d in j.values()),
                           "pass_A": None if j["A"]["pass_rate"] is None else rate(j["A"]["pass_rate"]),
                           "pass_candidate": None if j["candidate"]["pass_rate"] is None else rate(j["candidate"]["pass_rate"])}
    return out


def run_all(cfg: dict, judge: str, base: Path) -> dict:
    impl, over = pick_impl(cfg), grader_overrides(cfg)
    runs = {}
    for key, variant in (("A", cfg["baseline_variant"]), ("candidate", cfg["candidate_variant"])):
        out = base / f"release-{variant}"
        engine.run_suite(cfg["suite"], variant, impl=impl, out=out, grader_overrides=over)
        runs[key] = out
        recs = read_jsonl(out / "trials.jsonl")
        if any(r["status"] == "replay_miss" for r in recs):
            raise SystemExit(f"{variant}: replay misses in the release run; a recording is missing")
    return build_summary(cfg, runs, judge, import_file(cfg["release"]["gate"], "learner_gate_release"))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    opt = lambda f, d=None: argv[argv.index(f) + 1] if f in argv else d  # noqa: E731
    cfg = load_config()
    judge = opt("--judge", cfg["release"]["judge"])
    if judge == "d1r1e1":
        judge = "v3"
    try:
        summary = run_all(cfg, judge, Path(opt("--out", ROOT / "runs")))
    except NotImplementedError as err:
        print(err)
        return 1
    SUMMARY.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    s = summary
    print(f"release suite on {s['dataset_v2_hash'][:12]} (dataset v2), runner {s['runner']}, judge {s['judge']}")
    for f in ("triage", "reply"):
        d = s[f]
        print(f"{f}: A {100 * d['A']:.1f}%, candidate {100 * d['candidate']:.1f}%, difference {100 * d['diff']:+.1f} points, 95% interval ({100 * d['lo']:+.1f}, {100 * d['hi']:+.1f}): {d['verdict']}")
    a = s["agent"]
    print(f"agent (40 tasks, 5 trials): pass^1 A {100 * a['pass1_A']:.1f}%, candidate {100 * a['pass1_candidate']:.1f}%; pass^4 A {100 * a['pass4_A']:.1f}%, candidate {100 * a['pass4_candidate']:.1f}%")
    print(f"gate on the candidate against A: exit {s['gate']['exit']}" + (f" ({s['gate']['block_reason']})" if s['gate']['block_reason'] else ""))
    for line in s["judge_result"]["status"]:
        print(line)
    print(f"summary: {SUMMARY.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
