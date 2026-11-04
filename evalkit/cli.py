"""`python -m evalkit <command>`. Replay only: no command here calls a model."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from evalkit import engine, stats
from evalkit.suites import ROOT, case_scores, read_trials, run_path

LATER = {
    "notes": "2.5", "taxonomy-check": "2.6", "criteria-check": "2.6", "dataset": "3.7", "label": "5.7", "kappa": "5.7",
    "judge-eval": "5.8", "choose": "5.8", "judge-probes": "5.8", "judge-lint": "5.8", "gate": "9.7",
    "make-ci-branches": "9.9", "monitor": "10.6", "select-traces": "10.7",
}
CH6 = ROOT / "challenges" / "challenge-6-harness"
# Commands that exist now: name -> (module, function taking the rest of the arguments). The others in LATER are stubs.
LIVE = {"notes": ("evalkit.notes", "main"), "taxonomy-check": ("evalkit.taxonomy", "main"),
        "criteria-check": ("evalkit.criteria", "main"), "dataset": ("evalkit.dataset_cli", "main"),
        "label": ("evalkit.judges_cli", "label_main"), "kappa": ("evalkit.judges_cli", "kappa_main"),
        "judge-eval": ("evalkit.judges_cli", "judge_eval_main"), "choose": ("evalkit.judges_cli", "choose_main"),
        "judge-probes": ("evalkit.judges_cli", "probes_main"), "gate": ("evalkit.gate_cli", "gate_main"),
        "make-ci-branches": ("evalkit.ci_branches", "main"), "monitor": ("evalkit.monitor_cli", "monitor_main"),
        "select-traces": ("evalkit.monitor_cli", "select_traces_main")}


# --- doctor ---------------------------------------------------------------------------------------

def cmd_doctor(args) -> int:
    ok = True
    v = sys.version_info
    lines = []
    if v >= (3, 11):
        lines.append(f"OK python {v.major}.{v.minor}.{v.micro} (3.11 or newer is needed)")
    else:
        ok = False
        lines.append(f"FAIL python {v.major}.{v.minor}.{v.micro}: 3.11 or newer is needed")
    try:
        pk = {name: importlib.metadata.version(name) for name in ("pytest", "pydantic")}
        lines.append("OK packages " + ", ".join(f"{n} {ver}" for n, ver in pk.items()))
    except importlib.metadata.PackageNotFoundError as err:
        ok = False
        lines.append(f"FAIL packages: {err} is not installed (pip install -e .)")
    try:
        git = subprocess.run(["git", "--version"], capture_output=True, text=True, check=True).stdout.strip()
        lines.append(f"OK git ({git})")
    except (OSError, subprocess.CalledProcessError):
        ok = False
        lines.append("FAIL git: not found on PATH")
    try:
        from evalkit.replay import ReplayMiss, Store
        from product import triage

        store = Store.load("triage")
        req = triage.build_request("A", "Please change my login email to [email], thanks.")
        rec = store.lookup(req["key"], 1)
        try:
            store.lookup(triage.build_request("A", "a request that was never recorded")["key"], 1)
            raise AssertionError("an unrecorded request was found")
        except ReplayMiss:
            pass
        lines.append(f"OK replay: {len(store.index)} recorded triage lines; a recorded request hits, an unrecorded one raises ReplayMiss ({rec['key'][:12]})")
    except Exception as err:  # noqa: BLE001
        ok = False
        lines.append(f"FAIL replay: {type(err).__name__}: {err}")
    print("\n".join(lines))
    return 0 if ok else 1


# --- run --------------------------------------------------------------------------------------------

def _gaps_open() -> list[str]:
    found = []
    for path in sorted(CH6.glob("part-*/*.py")):
        if path.name.startswith("test_"):
            continue
        if 'NotImplementedError("YOUR TURN' in path.read_text(encoding="utf-8"):
            found.append(path.parent.name)
    return found


def cmd_run(args) -> int:
    if args.live:
        print("--live: live recording is the author's tool (tools/record.py). This runner replays recordings only.", file=sys.stderr)
        return 2
    runner = args.runner
    if runner == "auto":
        gaps = _gaps_open()
        runner = "reference" if gaps else "learner"
        why = f" (YOUR TURN gaps still open in {', '.join(gaps)}; use --runner learner to run yours)" if gaps else " (your challenge 6 scripts)"
        print(f"runner: {runner}{why}")
    else:
        print(f"runner: {runner}")
    if runner == "reference":
        from evalkit import runner_reference as impl
    else:
        from evalkit.runner_learner import load_impl
        impl = load_impl()
    try:
        s = engine.run_suite(args.suite, args.variant, impl=impl, trials=args.trials, workers=args.workers,
                             simulate_latency=args.simulate_latency, provider=args.provider, stop_after=args.stop_after,
                             resume=args.resume, out=args.out, rate_limit=args.rate_limit, timeout_s=args.timeout,
                             backoff_scale=args.backoff_scale)
    except engine.SimulatedCrash as crash:
        print(str(crash), file=sys.stderr)
        print(f"{crash.written} lines are in {Path(crash.out) / 'trials.jsonl'}; run again with --resume to finish", file=sys.stderr)
        return 1
    print(f"run id: {s['run_id']}")
    print(f"pass {s['passed']} of {s['records']}  (ok {s['ok']}, replay_miss {s['replay_miss']}, failed {s['failed']})")
    if s["replay_miss"]:
        print(f"replay_miss: {s['replay_miss']} trials had no recording; no model was called")
    if args.provider == "fake" or s["retries"]:
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(s["retry_kinds"].items()))
        print(f"attempts {s['attempts']}, retries {s['retries']} ({kinds})")
    if args.resume:
        print(f"this invocation ran {s['written_now']} trials; the file now holds {s['records']}")
    print(f"workers {s['workers']}, elapsed {s['elapsed_s']:.1f} s")
    print(f"report: {Path(s['out']) / 'report.md'}")
    return 0


# --- diff ---------------------------------------------------------------------------------------------

def _grades(g: dict) -> str:
    return " ".join(f"{k}:{'ok' if v else 'FAIL'}" for k, v in g.items()) or "-"


def _short(o) -> str:
    return "-" if o is None else " ".join(str(o).split())


def _cell(r: dict) -> str:
    """What a run recorded for a trial: the output; for an agent trial also the tool calls in order."""
    out = _short(r.get("output"))
    if r["feature"] == "agent":
        calls = " > ".join(r.get("calls") or []) or "no calls"
        out = f"[{calls}] {out[:60]}" if r.get("output") else f"[{calls}]"
    return out


def _verdict(r) -> str:
    return "pass" if r.get("passed") else "FAIL"


def _exp(r) -> str:
    e = r.get("expected")
    return "-" if not e else f"{e['category']}, urgent {str(e['urgent']).lower()}"


def cmd_diff(args) -> int:
    from evalkit.runner_reference import diff_runs

    a, b = read_trials(args.run_a), read_trials(args.run_b)
    flips = {(r["feature"], r["case_id"]): r["direction"] for r in diff_runs(a, b)}
    first_a = {(r["feature"], r["case_id"]): r for r in sorted(a, key=lambda r: -r["trial"])}
    first_b = {(r["feature"], r["case_id"]): r for r in sorted(b, key=lambda r: -r["trial"])}
    keys = [k for k in dict.fromkeys((r["feature"], r["case_id"]) for r in a) if k in first_b]
    up = sum(d == "to_pass" for d in flips.values())
    print(f"diff {run_path(args.run_a).name} {run_path(args.run_b).name}: {len(keys)} cases compared, {len(flips)} flipped "
          f"(to pass under B: {up}, to fail under B: {len(flips) - up})")
    shown = keys if len(keys) <= 20 else [k for k in keys if k in flips]
    if len(keys) > 20:
        print(f"(only the {len(shown)} flipped cases are listed)")
    print()
    print("| case id | expected | A output and grade | B output and grade | flipped |")
    print("|---|---|---|---|---|")
    for k in shown:
        ra, rb = first_a[k], first_b[k]
        print(f"| {k[1]} | {_exp(ra)} | {_cell(ra)} {_verdict(ra)} | {_cell(rb)} {_verdict(rb)} | {flips.get(k, '-')} |")
    return 0


# --- check-runner ----------------------------------------------------------------------------------------

def cmd_check_runner(args) -> int:
    env = dict(os.environ)
    env["EVALKIT_RUNNER"] = args.runner
    proc = subprocess.run([sys.executable, "-m", "pytest", str(CH6), "-q", "-p", "no:cacheprovider", "--tb=line"],
                          capture_output=True, text=True, cwd=ROOT, env=env)
    tail = [l for l in proc.stdout.splitlines() if l.strip()]
    print("\n".join(tail[-12:]))
    passed = re.search(r"(\d+) passed", proc.stdout)
    failed = re.search(r"(\d+) failed", proc.stdout)
    n_pass, n_fail = int(passed.group(1)) if passed else 0, int(failed.group(1)) if failed else 0
    if proc.returncode == 0:
        print(f"check-runner: {n_pass} tests passed ({args.runner} runner). Your runner is ready.")
    else:
        print(f"check-runner: {n_fail} failed, {n_pass} passed ({args.runner} runner). Fix the failing tests, or use --runner reference.")
    return proc.returncode


# --- stats -----------------------------------------------------------------------------------------------

def _scores_by_feature(run) -> dict:
    out: dict = {}
    for (feature, cid), score in sorted(case_scores(read_trials(run)).items()):
        out.setdefault(feature, {})[cid] = score
    return out


def cmd_stats(args) -> int:
    sub = args.stats_cmd
    if sub in ("interval", "bootstrap"):
        for feature, scores in _scores_by_feature(args.run).items():
            xs = list(scores.values())
            n = len(xs)
            m, se, (lo, hi) = stats.se_interval(xs)
            blo, bhi = stats.bootstrap(xs)
            print(f"{feature}: {n} cases, mean {m:.4f}")
            if sub == "interval":
                print(f"  standard error {se:.4f}, normal 95% interval ({lo:.4f}, {hi:.4f}), clipped to 0 and 1")
            print(f"  bootstrap 95% interval ({blo:.4f}, {bhi:.4f}) from 10000 resamples of cases, seed 7")
            fails = sum(1 for x in xs if x < 1.0)
            if fails == 0:
                print(f"  no failing case: rule of three, the fail rate is at most {stats.rule_of_three(n):.4f} (3 / {n})")
    elif sub == "paired":
        a, b = _scores_by_feature(args.run_a), _scores_by_feature(args.run_b)
        for feature in a:
            if feature not in b:
                continue
            ids = sorted(set(a[feature]) & set(b[feature]))
            diffs = [b[feature][i] - a[feature][i] for i in ids]
            m, (lo, hi) = stats.paired_bootstrap(diffs)
            print(f"{feature}: {len(ids)} cases, mean difference B minus A {m:+.4f}, 95% interval ({lo:+.4f}, {hi:+.4f}): {stats.verdict((lo, hi))}")
    elif sub == "judge-interval":
        path = run_path(args.run)
        path = path if path.suffix == ".json" else path.with_suffix(".json")
        if not path.exists():
            print(f"{path}: no test report yet; run `python -m evalkit judge-eval --split test` first")
            return 1
        r = json.loads(path.read_text(encoding="utf-8"))
        n_fail, n_pass = r["tp"] + r["fn"], r["tn"] + r["fp"]
        print(f"judge {r['judge']} on the test split ({r['label_source']} labels), fail is the positive class")
        for name, k, n in (("TPR", r["tp"], n_fail), ("TNR", r["tn"], n_pass)):
            lo, hi = stats.rate_interval(k, n)
            edge = " (rule of three: all correct)" if k == n else " (rule of three: none correct)" if k == 0 else ""
            print(f"{name} {k}/{n} = {k / n:.4f}, 95% interval ({max(0.0, lo):.4f}, {hi:.4f}){edge}")
        print(f"one reply moves a rate by {100 / n_fail:.1f} points (fails) or {100 / n_pass:.1f} points (passes); the bootstrap resamples the {n_fail} and {n_pass} verdicts, seed 7")
    elif sub == "sign-test":
        for feature in sorted({r["feature"] for r in read_trials(args.run_a)}):
            def passes(run):
                return {r["case_id"]: bool(r.get("passed")) for r in read_trials(run) if r["feature"] == feature and r["trial"] == args.trial}
            pa, pb = passes(args.run_a), passes(args.run_b)
            ids = sorted(set(pa) & set(pb))
            x = sum(pb[i] and not pa[i] for i in ids)
            y = sum(pa[i] and not pb[i] for i in ids)
            print(f"{feature}, trial {args.trial}: {len(ids)} cases, flips to pass {x}, flips to fail {y}, exact two-sided p = {stats.sign_test(x, y):.4f}")
    elif sub == "passk":
        by: dict = {}
        for r in read_trials(args.run):
            by.setdefault((r["feature"], r["case_id"]), []).append(bool(r.get("passed")))
        for feature in sorted({f for f, _ in by}):
            vals = []
            for (f, _), ps in by.items():
                if f == feature:
                    vals.append(stats.pass_hat_k(sum(ps), len(ps), args.k))
            print(f"{feature}: {len(vals)} cases, pass^{args.k} = {sum(vals) / len(vals):.4f}")
    return 0


# --- parser ------------------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m evalkit", description="FreshMarket eval kit (replay only)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check Python, packages, Git and replay; print four OK lines")

    r = sub.add_parser("run", help="run a suite and write runs/<id>/trials.jsonl and report.md")
    r.add_argument("--suite", required=True)
    r.add_argument("--variant", required=True)
    r.add_argument("--trials", type=int)
    r.add_argument("--runner", choices=["auto", "reference", "learner"], default="auto")
    r.add_argument("--provider", choices=["replay", "fake"], default="replay")
    r.add_argument("--workers", type=int, default=1)
    r.add_argument("--simulate-latency", type=float, default=0.0, metavar="F")
    r.add_argument("--stop-after", type=int, metavar="N")
    r.add_argument("--resume", action="store_true")
    r.add_argument("--out")
    r.add_argument("--rate-limit", type=float, metavar="PER_SECOND", help="simulated rate limit: refuse calls above this rate")
    r.add_argument("--timeout", type=float, default=30.0, metavar="SECONDS", help="per-call timeout, enforced by the provider")
    r.add_argument("--backoff-scale", type=float, default=1.0, metavar="F", help="multiply every retry wait by F (0.01 for a quick demo)")
    r.add_argument("--live", action="store_true", help="not available in this runner")

    d = sub.add_parser("diff", help="per-case diff of two runs")
    d.add_argument("run_a")
    d.add_argument("run_b")

    c = sub.add_parser("check-runner", help="run the challenge 6 tests against your runner")
    c.add_argument("--runner", choices=["learner", "reference"], default="learner")

    s = sub.add_parser("stats", help="seeded statistics on a run")
    ss = s.add_subparsers(dest="stats_cmd", required=True)
    for name in ("interval", "bootstrap"):
        ss.add_parser(name).add_argument("run")
    pp = ss.add_parser("paired")
    pp.add_argument("run_a")
    pp.add_argument("run_b")
    ss.add_parser("judge-interval", help="interval of the chosen judge's test TPR and TNR").add_argument("run")
    st = ss.add_parser("sign-test")
    st.add_argument("run_a")
    st.add_argument("run_b")
    st.add_argument("--trial", type=int, default=1)
    pk = ss.add_parser("passk")
    pk.add_argument("run")
    pk.add_argument("--k", type=int, required=True)

    for name in LATER:
        sub.add_parser(name, help="added in a later chapter", add_help=False)
    return p


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in LIVE:
        import importlib

        module, attr = LIVE[argv[0]]
        return getattr(importlib.import_module(module), attr)(argv[1:])
    if argv and argv[0] in LATER:
        print(f"{argv[0]}: added in a later chapter ({LATER[argv[0]]})")
        return 0
    args = build_parser().parse_args(argv)
    handlers = {"doctor": cmd_doctor, "run": cmd_run, "diff": cmd_diff, "check-runner": cmd_check_runner, "stats": cmd_stats}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
