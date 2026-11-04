"""Suites, run folders, summaries and reports (shipped, finished: the learner reads it and calls it)."""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

from evalkit.stats import percentile

ROOT = Path(__file__).resolve().parents[1]
SUITES = ROOT / "suites"
RUNS = ROOT / "runs"


def read_jsonl(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def load_suite(name_or_path) -> dict:
    """A suite is a TOML file: name, description and one or more [[part]] tables (feature, dataset, trials, graders)."""
    p = Path(str(name_or_path))
    if not p.suffix:
        p = SUITES / f"{p.name}.toml"
    if not p.exists():
        raise SystemExit(f"no suite {name_or_path}: looked for {p}")
    suite = tomllib.loads(p.read_text(encoding="utf-8"))
    suite.setdefault("name", p.stem)
    return suite


def load_cases(part: dict, root: Path = ROOT) -> list[dict]:
    path = Path(part["dataset"])
    path = path if path.is_absolute() else root / path
    rows = read_jsonl(path)
    if "cases" in part:
        by_id = {r["id"]: r for r in rows}
        missing = [c for c in part["cases"] if c not in by_id]
        if missing:
            raise SystemExit(f"suite names cases that are not in {path.name}: {missing}")
        return [by_id[c] for c in part["cases"]]
    if "split" in part:
        rows = [r for r in rows if r.get("split") == part["split"]]
    return rows


def run_path(run: str | Path) -> Path:
    """`m1-triage-A`, `runs/m1-triage-A` or a full path all name the same run folder."""
    p = Path(str(run))
    if p.exists():
        return p
    return RUNS / p.name


def read_trials(run: str | Path) -> list[dict]:
    return read_jsonl(run_path(run) / "trials.jsonl")


def summarise(records: list[dict]) -> dict:
    ok = [r for r in records if r["status"] == "ok"]
    lat = sorted(r["latency_ms"] for r in ok if r.get("latency_valid") and r.get("latency_ms") is not None)
    grader_fails: dict = {}
    for r in ok:
        for g, v in r["grades"].items():
            if not v:
                grader_fails[g] = grader_fails.get(g, 0) + 1
    kinds: dict = {}
    for r in records:
        for k in r.get("retried", []):
            kinds[k] = kinds.get(k, 0) + 1
    return {
        "records": len(records),
        "ok": len(ok),
        "replay_miss": sum(r["status"] == "replay_miss" for r in records),
        "failed": sum(r["status"] == "failed" for r in records),
        "passed": sum(bool(r.get("passed")) for r in records),
        "grader_fails": grader_fails,
        "attempts": sum(r.get("attempts", 1) for r in records),
        "retries": sum(len(r.get("retried", [])) for r in records),
        "retry_kinds": kinds,
        "tokens_in": sum(r.get("tokens_in") or 0 for r in ok),
        "tokens_out": sum(r.get("tokens_out") or 0 for r in ok),
        "latency_valid_n": len(lat),
        "latency_mean_ms": round(sum(lat) / len(lat), 1) if lat else None,
        "latency_p95_ms": percentile(lat, 0.95) if lat else None,
    }


def case_scores(records: list[dict]) -> dict:
    """(feature, case_id) -> mean of the trial passes. The case is the unit."""
    acc: dict = {}
    for r in records:
        acc.setdefault((r["feature"], r["case_id"]), []).append(1.0 if r.get("passed") else 0.0)
    return {k: sum(v) / len(v) for k, v in acc.items()}


def write_report(out: Path, meta: dict, records: list[dict], skipped: list[str]) -> str:
    s = summarise(records)
    lines = [f"# Run {out.name}", "",
             f"- suite: {meta['suite']}",
             f"- variant: {meta['variant']} (model {meta['model']})",
             f"- provider: {meta['provider']}",
             f"- trials per case: {meta['trials']}",
             f"- trial records: {s['records']} (ok {s['ok']}, replay_miss {s['replay_miss']}, failed {s['failed']})",
             f"- passed: {s['passed']} of {s['records']}", ""]
    lines += ["## By feature", "", "| feature | cases | trial records | passed | pass rate |", "|---|---|---|---|---|"]
    for feature in meta["features"]:
        rs = [r for r in records if r["feature"] == feature]
        cases = len({r["case_id"] for r in rs})
        p = sum(bool(r.get("passed")) for r in rs)
        rate = f"{100 * p / len(rs):.1f}%" if rs else "n/a"
        lines.append(f"| {feature} | {cases} | {len(rs)} | {p} | {rate} |")
    lines += ["", "## Failures by grader", ""]
    if s["grader_fails"]:
        lines += ["| grader | failed trials |", "|---|---|"] + [f"| {g} | {n} |" for g, n in sorted(s["grader_fails"].items())]
    else:
        lines.append("No grader failed.")
    failed_ids = sorted({r["case_id"] for r in records if not r.get("passed")})
    lines += ["", f"Cases with a failed trial: {len(failed_ids)}" + (f" ({', '.join(failed_ids[:30])}{' ...' if len(failed_ids) > 30 else ''})" if failed_ids else ""), ""]
    if s["replay_miss"]:
        miss_ids = sorted({r["case_id"] for r in records if r["status"] == "replay_miss"})
        lines += ["## Replay misses", "", f"{s['replay_miss']} trial(s) had no recording and were not run ({len(miss_ids)} cases). A miss never calls a model.", ""]
    lines += ["## Cost and time (from the recordings)", "",
              f"- tokens in: {s['tokens_in']}, tokens out: {s['tokens_out']}",
              f"- latency, valid trials only: n {s['latency_valid_n']}, mean {s['latency_mean_ms']} ms, p95 {s['latency_p95_ms']} ms (nearest rank)"]
    lines += ["", "## Attempts", "",
              f"- attempts: {s['attempts']}, retries: {s['retries']} {s['retry_kinds'] if s['retry_kinds'] else ''}".rstrip()]
    if skipped:
        lines += ["", "## Not run", ""] + [f"- {x}" for x in skipped]
    text = "\n".join(lines) + "\n"
    (out / "report.md").write_text(text, encoding="utf-8")
    return text
