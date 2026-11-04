"""Challenge 11, part 1. One test per checkpoint. They fail on the starter (release_config.toml is unfilled). Replay only.

The judge numbers need the capstone judge recordings (reference/results/capstone-recordings-needed.md). While a recording is missing the test
SKIPS the judge assertions with the 'not recorded yet' line; it never passes on a guess."""
import importlib.util
import json
import re
from pathlib import Path

import pytest

from evalkit import capstone
from judges.parts import ALL_JUDGES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def glue():
    spec = importlib.util.spec_from_file_location("run_release_glue", HERE / "run_release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    g = glue()
    cfg = g.load_config()
    judge = "v3" if cfg["release"]["judge"] == "d1r1e1" else cfg["release"]["judge"]
    return cfg, judge, g.run_all(cfg, judge, tmp_path_factory.mktemp("release"))


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def test_checkpoint_1(release):
    cfg, judge, s = release                      # the config resolved and both runs finished with no replay miss (run_all stops on a miss)
    assert judge in ALL_JUDGES, "the judge must be one of the 14 recorded judges (v3, or a builder id other than d1r1e1)"
    assert (capstone.dev_tpr(judge) or 0) >= 0.85, "the 5.8 rule allows only judges with dev TPR of at least 0.85; use v3 if yours was not accepted"
    assert cfg["release"]["runner"] in ("learner", "reference")
    body = section("Checkpoint 1")
    assert PLACEHOLDER not in body
    assert re.search(rf"^Runner: {cfg['release']['runner']}", body, flags=re.M), "write the line 'Runner: learner' or 'Runner: reference' (and why)"
    assert re.search(rf"^Judge: {judge}\b", body, flags=re.M)
    assert s["release_suite_trials"] == 5 and s["triage"]["n"] == 200 and s["reply"]["n"] == 200
    if not s["judge_result"]["recorded"]:
        pytest.skip("; ".join(s["judge_result"]["status"]))
    assert s["judge_result"]["judged_n"] == 72, "72 refund replies of dataset v2 must be judged"


def test_checkpoint_2(release):
    cfg, judge, s = release
    assert s["gate"]["exit"] in (0, 1)
    body = section("Checkpoint 2")
    assert PLACEHOLDER not in body
    assert re.search(rf"^Gate exit code on the candidate: {s['gate']['exit']}$", body, flags=re.M)
    for f in ("triage", "reply"):
        d = s[f]
        assert d["lo"] <= d["diff"] <= d["hi"]
        line = (f"{f.capitalize()}: A {100 * d['A']:.1f}%, candidate {100 * d['candidate']:.1f}%, difference {100 * d['diff']:+.1f} points, "
                f"95% interval ({100 * d['lo']:+.1f}, {100 * d['hi']:+.1f}): {d['verdict']}")
        assert re.search("^" + re.escape(line) + "$", body, flags=re.M), f"the {f} line must match your run"
        assert s[f"{f}_slices"], f"the per-slice table for {f} is missing"
    for row in s["reply_slices"]:
        assert row["slice"] in body, "the per-slice table of reply must list every slice"
    assert s["reply_weak_slice"]["slice"] in body
    assert s["gate"]["exit"] == 1 and "must-pass agent case r28" in "\n".join(s["gate"]["block_lines"]), \
        "the tagged agent task r28 passes 4 of 5 trials on the candidate: the must-pass check blocks it"


def test_checkpoint_3(release):
    cfg, judge, s = release
    body = section("Checkpoint 3")
    assert PLACEHOLDER not in body
    for variant in ("A", "candidate"):
        for k in (1, 4):
            want = s["agent"][f"pass{k}_{variant}"]
            hit = re.search(rf"^pass\^{k} {variant}: ([\d.]+)%", body, flags=re.M)
            assert hit and abs(float(hit.group(1)) / 100 - want) <= 0.005, f"write 'pass^{k} {variant}: N%'"
    for row in s["mustpass"]["cases"]:
        assert re.search(rf"^\| {row['case']} \| {row['A']} of 5 \| {row['candidate']} of 5 \|", body, flags=re.M), f"must-pass table row for {row['case']}"
    c = s["cost"]
    for name in ("cost1k_A", "cost1k_candidate"):
        assert re.search(rf"^{name}: {c[name]:.4f}\b|^{name}: {c[name]:.2f}\b", body, flags=re.M), f"write '{name}: ...'"
    assert re.search(rf"^p95_A_ms: {c['p95_A_ms']}$", body, flags=re.M) and re.search(rf"^p95_candidate_ms: {c['p95_candidate_ms']}$", body, flags=re.M)
    assert (HERE / "summary.json").exists(), "run run_release.py: it writes summary.json, the file the report check reads"
    written = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
    for key in ("triage", "reply", "agent", "mustpass", "cost", "gate", "reply_weak_slice", "dataset_v2_hash"):
        assert key in written, f"summary.json needs {key}"
        assert written[key] == s[key], f"summary.json differs from a fresh run in {key}; run run_release.py again"
