"""Challenge 9, part 1: the ship gate. One script decides whether a change can merge.

    python -m evalkit gate runs/<id> --baseline baselines/full-A
    python -m evalkit gate --init-margin --baseline baselines/full-A

Exit code 0 when no check printed a BLOCK line (WARN lines are printed), 1 when one did, 2 when the gate could not run.

How the gate scores (brief, section "Suites, judges, tasks and the gate"):
  * A case's score is the mean of its trial grades. A feature's score (triage, reply, agent) is the mean over its non-quarantined cases.
  * Must-pass cases carry `must_pass: true` in their trial records (the author tagged them in canonical v1 and in datasets/agent_tasks.jsonl).
  * A case is a stable pass in the baseline when it passes every trial (5 of 5). A case that passes 1 to 4 of 5 in the baseline is quarantined:
    it is left out of feature scores and of warnings, and listed.
  * A BLOCK is: a must-pass case under 5 of 5, a feature score under its floor, a feature drop larger than its margin, a budget over its
    limit, or a replay miss. A WARN is: a stable-pass case that is not must-pass now passes fewer than 5 of 5 while its feature's drop is
    within the margin.

Shipped and read, not written: Run, quarantined_cases, feature_scores, p95_ms, request_cost, init_margin, run_checks, exit_code, main.
Fill the five YOUR TURN gaps. Each takes a Run and returns a list of lines; a line is (level, text) with level "BLOCK", "WARN" or "INFO".
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from evalkit import stats  # noqa: E402
from evalkit.suites import read_jsonl, run_path  # noqa: E402

FEATURES = ("triage", "reply", "agent")
CONFIG = HERE / "gate.toml"
PRICES = ROOT / "product" / "prices.toml"
SINGLE_CALL = ("triage", "reply")  # a request is one model call; an agent trial is a whole task of several calls


# --- shipped: the run, the quarantine filter, the helpers ---------------------------------------------------------------------

class Run:
    """Trial records grouped by case. `quarantined` is the set of (feature, case_id) the baseline put aside."""

    def __init__(self, records, quarantined=frozenset()):
        self.records = records
        self.quarantined = set(quarantined)
        self.cases: dict = {}      # (feature, case_id) -> list of True/False, one per trial
        self.must_pass: set = set()
        self.misses: list = []     # trial records with status replay_miss
        for r in self.records:
            key = (r["feature"], r["case_id"])
            self.cases.setdefault(key, []).append(bool(r.get("passed")))
            if r.get("must_pass"):
                self.must_pass.add(key)
            if r.get("status") == "replay_miss":
                self.misses.append(r)

    def score(self, key) -> float:
        passes = self.cases[key]
        return sum(passes) / len(passes)

    def feature_scores(self) -> dict:
        """Feature -> mean case score over the cases that are not quarantined."""
        out = {}
        for f in FEATURES:
            xs = [self.score(k) for k in sorted(self.cases) if k[0] == f and k not in self.quarantined]
            if xs:
                out[f] = sum(xs) / len(xs)
        return out

    def stable(self, key) -> bool:
        return all(self.cases[key])


def quarantined_cases(baseline_records: list) -> set:
    """The quarantine filter: cases that pass 1 to 4 of their 5 trials in the baseline (flaky, so a change cannot be judged on them)."""
    base = Run(baseline_records)
    return {k for k, passes in base.cases.items() if 0 < sum(passes) < len(passes)}


def p95_ms(latencies) -> int:
    """Nearest-rank p95: the value at rank ceil(0.95 x n) of the sorted latencies."""
    return stats.percentile(sorted(latencies), 0.95)


def prices() -> dict:
    return tomllib.loads(PRICES.read_text(encoding="utf-8"))


def request_cost(record: dict, table: dict | None = None) -> float:
    """Dollars for one trial record, from its tokens and the price per million tokens of its model (product/prices.toml)."""
    table = table or prices()
    p = table[record["model"]]
    return ((record.get("tokens_in") or 0) * p["input"] + (record.get("tokens_out") or 0) * p["output"]) / 1e6


def budget_numbers(run: Run, table: dict | None = None) -> dict:
    """Cost per 1,000 requests and the p95 over valid latencies, for triage and reply records (one model call each)."""
    recs = [r for r in run.records if r["feature"] in SINGLE_CALL and r.get("status") == "ok"]
    cost = sum(request_cost(r, table) for r in recs) / len(recs) * 1000 if recs else 0.0
    lat = [r["latency_ms"] for r in recs if r.get("latency_valid") and r.get("latency_ms") is not None]
    return {"requests": len(recs), "cost_per_1k": cost, "latency_n": len(lat), "p95_ms": p95_ms(lat) if lat else None}


def load_config(path: Path = CONFIG) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8"))


def exit_code(lines) -> int:
    """0 when no line is a BLOCK, 1 when one is. WARN and INFO lines never fail the gate."""
    return 1 if any(level == "BLOCK" for level, _ in lines) else 0


# --- YOUR TURN: the five checks -------------------------------------------------------------------------------------------------

def check_must_pass(run: Run) -> list:
    """Every tagged must-pass case (run.must_pass) must pass all of its trials. A case that passed fewer is a line
    ("BLOCK", "must-pass reply case t164 passed 3 of 5 trials"). run.cases[key] is the list of trial results of (feature, case_id)."""
    raise NotImplementedError("YOUR TURN: one BLOCK line for each must-pass case with a failed trial")


def check_floor(run: Run, floors: dict) -> list:
    """floors: feature -> lowest allowed feature score. run.feature_scores() gives the scores. A feature under its floor is a
    ("BLOCK", "reply score 0.812 is under its floor 0.850") line."""
    raise NotImplementedError("YOUR TURN: compare each feature score with its floor")


def check_margin(run: Run, baseline: Run, margins: dict) -> list:
    """margins: feature -> noise margin. For each feature, drop = baseline score - run score (both over the same non-quarantined cases).
    A drop larger than the margin is a BLOCK line. While a feature's drop is within its margin, every stable-pass baseline case of that
    feature that is not must-pass and now passes fewer than all its trials is a WARN line. Quarantined cases get one INFO line for each
    feature, printed first, even when the feature blocks: how many were left out. baseline.stable(key), baseline.must_pass and run.quarantined are what you need."""
    raise NotImplementedError("YOUR TURN: BLOCK for a drop over the margin; WARN for a slipped stable case inside the margin; INFO for the quarantine")


def check_budget(run: Run, budget: dict) -> list:
    """budget: {"cost_per_1k": dollars, "p95_ms": milliseconds}. budget_numbers(run) gives the run's cost per 1,000 requests and its
    nearest-rank p95 over valid latencies. Always print one INFO line per budget with the number and the limit; over the limit is a BLOCK line."""
    raise NotImplementedError("YOUR TURN: INFO line per budget; BLOCK when a number is over its limit")


def check_misses(run: Run) -> list:
    """`evalkit run` writes a replay_miss line into trials.jsonl for a request it could not find in the recordings. run.misses holds those
    records. The gate cannot judge a change it could not run: one BLOCK line per feature that names how many trials were missing."""
    raise NotImplementedError("YOUR TURN: a BLOCK line for the replay misses")


# --- shipped: put the checks together --------------------------------------------------------------------------------------------

def run_checks(run: Run, baseline: Run, cfg: dict) -> list:
    lines = []
    for name, check in (("check_must_pass", lambda: check_must_pass(run)), ("check_floor", lambda: check_floor(run, cfg["floor"])),
                        ("check_margin", lambda: check_margin(run, baseline, cfg["margin"])), ("check_budget", lambda: check_budget(run, cfg["budget"])),
                        ("check_misses", lambda: check_misses(run))):
        got = check()
        lines += got
        if not any(level in ("BLOCK", "WARN") for level, _ in got):
            lines.append(("PASS", f"{name}"))
    return lines


def init_margin(baseline_records: list, path: Path = CONFIG) -> dict:
    """The margin of each feature, computed once from the baseline: half the width of the case-level 95% bootstrap interval of the
    feature's score over the baseline's non-quarantined cases. Written to gate.toml under [margin]."""
    base = Run(baseline_records, quarantined_cases(baseline_records))
    margins = {}
    for f in FEATURES:
        xs = [base.score(k) for k in sorted(base.cases) if k[0] == f and k not in base.quarantined]
        if xs:
            lo, hi = stats.bootstrap(xs)
            margins[f] = round((hi - lo) / 2, 4)
    cfg = load_config(path)
    cfg["margin"] = margins
    write_config(cfg, path)
    return margins


def write_config(cfg: dict, path: Path = CONFIG) -> None:
    out = ["# The ship gate's numbers. Floors and budgets are the author's; margins are written by `gate --init-margin`.", ""]
    for table, values in cfg.items():
        out.append(f"[{table}]")
        out += [f"{k} = {v}" for k, v in values.items()]
        out.append("")
    Path(path).write_text("\n".join(out), encoding="utf-8")


def load_records(path) -> list:
    p = run_path(path) if not Path(str(path)).exists() else Path(str(path))
    if not (p / "trials.jsonl").exists():
        p = ROOT / str(path)
    return read_jsonl(p / "trials.jsonl")


def gate(run_records: list, baseline_records: list, cfg: dict) -> tuple[list, int]:
    q = quarantined_cases(baseline_records)
    lines = run_checks(Run(run_records, q), Run(baseline_records, q), cfg)
    return lines, exit_code(lines)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    opt = lambda f, d=None: argv[argv.index(f) + 1] if f in argv else d  # noqa: E731
    base_arg = opt("--baseline")
    if not base_arg:
        print("usage: gate RUN --baseline BASELINE | gate --init-margin --baseline BASELINE")
        return 2
    baseline = load_records(base_arg)
    if "--init-margin" in argv:
        m = init_margin(baseline)
        print(f"margins from {base_arg} (half-width of the case-level 95% bootstrap interval, non-quarantined cases): "
              + ", ".join(f"{f} {v}" for f, v in m.items()))
        print(f"written to {CONFIG.relative_to(ROOT).as_posix()}")
        return 0
    run_arg = next((a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--baseline")), None)
    if not run_arg:
        print("usage: gate RUN --baseline BASELINE")
        return 2
    cfg = load_config()
    if not cfg.get("margin"):
        print("gate.toml has no margins yet: run `python -m evalkit gate --init-margin --baseline baselines/full-A` once")
        return 2
    records = load_records(run_arg)
    print(f"gate: {run_arg} against {base_arg}")
    try:
        lines, code = gate(records, baseline, cfg)
    except NotImplementedError as err:
        print(err)
        return 2
    for level, text in lines:
        print(f"{level} {text}")
    print(f"result: {'BLOCK' if code else 'PASS'} (exit {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())
