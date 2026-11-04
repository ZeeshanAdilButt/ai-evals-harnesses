"""The run engine (shipped, finished). It calls the pieces the learner builds in challenge 6.

`impl` is any object with these names: get_grader, CachedProvider, SafeWriter, run_pool,
run_with_retries, resume_skip, MAX_ATTEMPTS. `evalkit.runner_reference` is the solved one;
`evalkit.runner_learner` loads the learner's three challenge scripts.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from evalkit.providers import FakeProvider, ProviderError, RateLimiter, ReplayProvider
from evalkit.replay import ReplayMiss
from evalkit.suites import ROOT, RUNS, load_cases, load_suite, read_jsonl, summarise, write_report
from evalkit.graders import agent as agent_graders
from product import reply, triage
from product.agent.agent import build_request as agent_request, run_task
from product.agent.store import load_orders

BUILDERS = {"triage": triage.build_request, "reply": reply.build_request}
FEATURES = ("triage", "reply", "agent")


def default_agent_graders() -> dict:
    """The reference agent graders by suite name. Each takes (trial, task): a trial has trajectory, final_state, customer_gave_up."""
    return {
        "agent_state": lambda trial, task: bool(agent_graders.grade_final_state(trial, task)["ok"]),
        "agent_trajectory": lambda trial, task: not agent_graders.trajectory_violations(task, trial["trajectory"], agent_graders.order_total(task)),
    }


class SimulatedCrash(Exception):
    """--stop-after N ends a run the way a crash would: the lines written so far stay, nothing else does."""

    def __init__(self, written: int, out: Path):
        super().__init__(f"stopped after {written} trials (simulated crash): no summary, no report")
        self.written = written
        self.out = out


def kind_of(error: BaseException) -> str:
    if isinstance(error, TimeoutError):
        return "timeout"
    status = getattr(error, "status", None)
    if status == 429:
        return "rate_limit"
    return "server_error" if status and status >= 500 else "error"


def default_run_id(suite: str, variant: str, provider: str, workers: int) -> str:
    return f"{suite}-{variant}" + ("-fake" if provider == "fake" else "") + (f"-w{workers}" if workers > 1 else "")


def make_provider(kind: str, feature: str, impl, simulate_latency: float, rate_limit):
    cache = impl.CachedProvider(feature)
    limiter = RateLimiter(rate_limit) if rate_limit else None
    kwargs = dict(lookup=lambda request, trial: cache.complete(request, trial),
                  simulate_latency=simulate_latency, limiter=limiter)
    if kind == "fake":
        return FakeProvider(feature, seed=7, **kwargs), cache
    return ReplayProvider(feature, **kwargs), cache


def run_suite(suite, variant: str, *, impl, trials: int | None = None, workers: int = 1,
              simulate_latency: float = 0.0, provider: str = "replay", stop_after: int | None = None,
              resume: bool = False, out=None, rate_limit: float | None = None, timeout_s: float = 30.0,
              backoff_scale: float = 1.0, sleep=time.sleep, root: Path = ROOT, grader_overrides: dict | None = None) -> dict:
    """grader_overrides: grader name -> function that replaces the shipped one for this run (the capstone passes the learner's).
    Triage and reply graders take (output, case); agent graders take (trial, task)."""
    if provider not in ("replay", "fake"):
        raise SystemExit(f"unknown provider {provider!r}: replay or fake (live runs need --live and are not part of this runner)")
    suite = load_suite(suite) if not isinstance(suite, dict) else suite
    out = Path(out) if out else RUNS / default_run_id(suite["name"], variant, provider, workers)
    out.mkdir(parents=True, exist_ok=True)
    trials_path = out / "trials.jsonl"
    if not resume:
        for name in ("trials.jsonl", "report.md", "meta.json"):
            (out / name).unlink(missing_ok=True)

    parts = suite["part"]
    feature_order = [p["feature"] for p in parts]
    overrides = grader_overrides or {}
    graders = {}
    agent_grade = {**default_agent_graders(), **{k: v for k, v in overrides.items() if k.startswith("agent_")}}
    for part in parts:
        if part["feature"] in BUILDERS:
            for g in part["graders"]:
                graders[g] = overrides.get(g) or impl.get_grader(g)  # an unknown name stops the run before any trial

    existing = read_jsonl(trials_path) if resume else []
    writer = impl.SafeWriter(trials_path)
    budget = stop_after
    written, crashed = 0, False
    skipped, order, models = [], {}, set()
    started = time.perf_counter()

    def run_sleep(seconds):
        sleep(seconds * backoff_scale)

    try:
        for part in parts:
            feature = part["feature"]
            if feature not in FEATURES:
                skipped.append(f"{feature}: not supported by this runner")
                continue
            cases = load_cases(part, root)
            n_trials = trials or part.get("trials", 1)
            by_id = {c["id"]: c for c in cases}
            for i, c in enumerate(cases):
                order[(feature, c["id"])] = i
            tasks = [(c["id"], variant, t) for c in cases for t in range(1, n_trials + 1)]
            done = {(r["case_id"], r["variant"], r["trial"]) for r in existing if r["feature"] == feature}
            tasks = impl.resume_skip(done, tasks)
            if budget is not None:
                if len(tasks) > budget:
                    tasks, crashed = tasks[:budget], True
                budget -= len(tasks)
            if feature == "agent":
                models.add(agent_request(variant, [])["model"])
                cache = impl.CachedProvider("agent")
                orders = load_orders(root / "datasets/agent/orders.json")

                def make_agent_work(task, by_id=by_id, cache=cache, orders=orders, part=part):
                    cid, var, trial = task

                    def work(call_timeout):
                        case = by_id[cid]
                        rec = {"feature": "agent", "case_id": cid, "variant": var, "trial": trial, "model": agent_request(var, [])["model"],
                               "key": agent_request(var, [{"role": "user", "content": case["opening"]}])["key"], "status": "ok",
                               "attempts": 1, "retried": [], "expected": None, "must_pass": bool(case.get("must_pass"))}
                        lines = []

                        def call(req):
                            line = cache.complete(req, trial)
                            lines.append(line)
                            return {"content": line["content"], "stop_reason": line["stop_reason"]}
                        try:
                            res = run_task(var, case, orders, call)
                            rec["grades"] = {g: bool(agent_grade[g](res, case)) for g in part["graders"]}
                            rec["passed"] = all(rec["grades"].values())
                            rec.update(output=res["final_message"], calls=[c["tool"] for c in res["trajectory"]], steps=res["steps"],
                                       stop=res["stop"], customer_gave_up=res["customer_gave_up"],
                                       tokens_in=sum(l.get("tokens_in") or 0 for l in lines), tokens_out=sum(l.get("tokens_out") or 0 for l in lines),
                                       latency_ms=sum(l.get("latency_ms") or 0 for l in lines),
                                       latency_valid=all(l.get("latency_valid") for l in lines))
                        except ReplayMiss as miss:
                            rec.update(status="replay_miss", error=str(miss), output=None, grades={}, passed=False, tokens_in=None,
                                       tokens_out=None, latency_ms=None, latency_valid=False)
                        writer.write(rec)
                        return rec
                    return work

                results = impl.run_pool([make_agent_work(t) for t in tasks], workers, timeout_s)
                for r in results:
                    if isinstance(r, BaseException):
                        raise r
                written += len(results)
                if crashed:
                    break
                continue
            prov, _cache = make_provider(provider, feature, impl, simulate_latency, rate_limit)
            build = BUILDERS[feature]
            models.add(build(variant, "x")["model"])

            def make_work(task, feature=feature, by_id=by_id, prov=prov, build=build, part=part):
                cid, var, trial = task

                def work(call_timeout):
                    case = by_id[cid]
                    request = build(var, case["text"])
                    rec = {"feature": feature, "case_id": cid, "variant": var, "trial": trial, "key": request["key"],
                           "model": request["model"], "status": "ok", "attempts": 1, "retried": [],
                           "expected": case.get("expected"), "must_pass": bool(case.get("must_pass")) if feature == "reply" else False}
                    try:
                        line, errors = impl.run_with_retries(lambda: prov.complete(request, trial, call_timeout), run_sleep)
                        rec["attempts"] = len(errors) + 1
                        rec["retried"] = [kind_of(e) for e in errors]
                        rec["output"] = line["output"]
                        rec["grades"] = {g: bool(graders[g](line["output"], case)) for g in part["graders"]}
                        rec["passed"] = all(rec["grades"].values())
                        rec.update(tokens_in=line.get("tokens_in"), tokens_out=line.get("tokens_out"),
                                   latency_ms=line.get("latency_ms"), latency_valid=line.get("latency_valid", False))
                    except ReplayMiss as miss:
                        rec.update(status="replay_miss", error=str(miss), output=None, grades={}, passed=False,
                                   tokens_in=None, tokens_out=None, latency_ms=None, latency_valid=False)
                    except (ProviderError, TimeoutError) as err:
                        rec.update(status="failed", error=f"{type(err).__name__}: {err}", output=None, grades={}, passed=False,
                                   attempts=impl.MAX_ATTEMPTS, retried=["error"] * (impl.MAX_ATTEMPTS - 1),
                                   tokens_in=None, tokens_out=None, latency_ms=None, latency_valid=False)
                    writer.write(rec)
                    return rec
                return work

            results = impl.run_pool([make_work(t) for t in tasks], workers, timeout_s)
            for r in results:
                if isinstance(r, BaseException):
                    raise r  # a bug in a piece of the runner is not a trial result
            written += len(results)
            if crashed:
                break
    finally:
        writer.close()

    if crashed:
        raise SimulatedCrash(written, out)

    records = read_jsonl(trials_path)
    records.sort(key=lambda r: (feature_order.index(r["feature"]), order[(r["feature"], r["case_id"])], r["variant"], r["trial"]))
    tmp = out / "trials.jsonl.tmp"
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records), encoding="utf-8")
    tmp.replace(trials_path)
    elapsed = time.perf_counter() - started

    run_features = [p["feature"] for p in parts if p["feature"] in FEATURES]
    trial_counts = sorted({trials or p.get("trials", 1) for p in parts if p["feature"] in FEATURES})
    meta = {"suite": suite["name"], "variant": variant, "model": ", ".join(sorted(models)), "provider": provider,
            "trials": trial_counts[0] if len(trial_counts) == 1 else "/".join(map(str, trial_counts)),
            "features": run_features}
    write_report(out, meta, records, skipped)
    summary = summarise(records)
    summary.update(run_id=out.name, out=str(out), elapsed_s=round(elapsed, 3), workers=workers, written_now=written)
    (out / "meta.json").write_text(json.dumps({**meta, "workers": workers, "simulate_latency": simulate_latency,
                                               "elapsed_s": round(elapsed, 3), "summary": summary}, indent=1, sort_keys=True),
                                   encoding="utf-8")
    return summary
