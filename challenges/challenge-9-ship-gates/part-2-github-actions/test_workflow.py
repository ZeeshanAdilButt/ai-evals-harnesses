"""Challenge 9, part 2. One test per checkpoint, plus the replay check of the two CI runs. Fails on the starter: the workflow file is not
filled (no .github/workflows/gate.yml), results.md is the empty template. Replay only; nothing is pushed.

The two CI branches are made by `python -m evalkit make-ci-branches`; a test cannot push, so checkpoint 2 makes them in a scratch
repository and, if your own copy already has them, checks yours too. The Actions logs themselves are the evidence in results.md."""
import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from evalkit import ci_branches, engine, runner_reference

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "gate.yml"
GATE = ROOT / "challenges" / "challenge-9-ship-gates" / "part-1-gate-script" / "gate.py"
PLACEHOLDER = "(fill in"


def results():
    return (HERE / "results.md").read_text(encoding="utf-8")


def section(title_start):
    for p in re.split(r"^## ", results(), flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def load_workflow():
    assert WORKFLOW.exists(), "copy ci/workflow-starter.yml to .github/workflows/gate.yml and fill the two gaps"
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "YOUR TURN" not in text, "a gap marker is still in the workflow file"
    return yaml.safe_load(text), text


def test_checkpoint_1():
    doc, text = load_workflow()
    on = doc.get("on", doc.get(True))     # YAML 1.1 reads the key `on` as the boolean True
    assert isinstance(on, dict) and "pull_request" in on, "the workflow must trigger on pull_request"
    assert "main" in (on["pull_request"] or {}).get("branches", []), "trigger on pull requests into main"
    assert "secrets." not in text, "the gate runs in replay and needs no secret"
    steps = doc["jobs"]["gate"]["steps"]
    runs = [s.get("run", "") for s in steps]
    run_i = next((i for i, r in enumerate(runs) if "evalkit run" in r and "--suite full" in r), None)
    gate_i = next((i for i, r in enumerate(runs) if "evalkit gate" in r), None)
    assert run_i is not None and gate_i is not None and run_i < gate_i, "the run step comes before the gate step"
    assert "baselines/full-A" in runs[gate_i] and "runs/pr" in runs[gate_i]
    body = section("Checkpoint 1")
    assert PLACEHOLDER not in body


def scratch_repo(tmp_path, monkeypatch, name="copy"):
    repo = tmp_path / name
    (repo / "ci").mkdir(parents=True)
    shutil.copytree(ROOT / "product" / "prompts", repo / "product" / "prompts")
    shutil.copytree(ROOT / "ci" / "patches", repo / "ci" / "patches")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    for args in (["init", "-q", "-b", "main"], ["add", "."], ["commit", "-q", "-m", "start"]):
        subprocess.run(["git", *args], cwd=repo, check=True, env=env, capture_output=True)
    for k in env:
        if k.startswith("GIT_"):
            monkeypatch.setenv(k, env[k])
    return repo


def test_make_ci_branches_changes_only_the_prompts_and_never_pushes(tmp_path, monkeypatch):
    repo = scratch_repo(tmp_path, monkeypatch)
    lines = []
    assert ci_branches.make_ci_branches(repo, out=lines.append) == 0
    text = "\n".join(lines)
    assert "git push origin ci/regression ci/harmless" in text and "Nothing was pushed" in text
    for branch, target in (("ci/regression", "reply_ci_regression.md"), ("ci/harmless", "reply_ci_harmless.md")):
        changed = subprocess.run(["git", "diff", "--name-only", f"main...{branch}"], cwd=repo, capture_output=True, text=True).stdout.split()
        assert changed and all(c.startswith("product/prompts/") for c in changed), changed
        patched = subprocess.run(["git", "show", f"{branch}:product/prompts/reply_A.md"], cwd=repo, capture_output=True).stdout
        assert patched == (ROOT / "product" / "prompts" / target).read_bytes(), "the patched prompt is exactly the one whose replies are recorded"
    assert subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip() == "main"
    assert ci_branches.make_ci_branches(repo, out=lines.append) == 1, "a second run refuses and changes nothing"
    dirty = scratch_repo(tmp_path, monkeypatch, "dirty")
    (dirty / "product" / "prompts" / "reply_A.md").write_text("changed", encoding="utf-8")
    assert ci_branches.make_ci_branches(dirty, out=lines.append) == 1, "a dirty tree is refused"
    assert not subprocess.run(["git", "branch", "--list", "ci/regression"], cwd=dirty, capture_output=True, text=True).stdout.strip()


def test_checkpoint_2():
    test_checkpoint_1()
    body = section("Checkpoint 2")
    assert PLACEHOLDER not in body
    prs = re.findall(r"pull request #(\d+)", body)
    assert len(set(prs)) == 2, "list two pull request numbers: 'pull request #N' for each"
    for branch in ("ci/regression", "ci/harmless"):     # your own copy, when you have made the branches
        have = subprocess.run(["git", "branch", "--list", branch], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if have:
            changed = subprocess.run(["git", "diff", "--name-only", f"main...{branch}"], cwd=ROOT, capture_output=True, text=True).stdout.split()
            assert changed and all(c.startswith("product/prompts/") for c in changed), f"{branch} may change files under product/prompts/ only"


def gate_module():
    spec = importlib.util.spec_from_file_location("learner_gate_ci", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ci_runs(tmp_path_factory):
    base = tmp_path_factory.mktemp("ci-runs")
    out = {}
    for variant in ("ci-regression", "ci-harmless"):
        engine.run_suite("full", variant, impl=runner_reference, out=base / variant)
        out[variant] = base / variant
    return out


def test_the_regression_run_blocks_and_the_harmless_run_passes_in_replay(ci_runs, capsys):
    gate = gate_module()
    assert gate.main([str(ci_runs["ci-regression"]), "--baseline", "baselines/full-A"]) == 1
    blocked = capsys.readouterr().out
    assert re.search(r"^BLOCK must-pass reply case t\d+", blocked, flags=re.M)
    assert not re.search(r"^BLOCK .*\b(triage|agent)\b", blocked, flags=re.M), "the patch edits only the reply prompt: triage and agent requests hit A's recordings"
    assert gate.main([str(ci_runs["ci-harmless"]), "--baseline", "baselines/full-A"]) == 0
    passed = capsys.readouterr().out
    assert "budget cost per 1,000 requests" in passed and "BLOCK" not in passed


def test_checkpoint_3(ci_runs, capsys):
    test_checkpoint_2()
    body = section("Checkpoint 3")
    assert PLACEHOLDER not in body
    links = re.findall(r"https://github\.com/\S+/actions/runs/\d+", body)
    assert len(set(links)) == 2, "put the two Actions run links in results.md"
    gate = gate_module()
    gate.main([str(ci_runs["ci-regression"]), "--baseline", "baselines/full-A"])
    blocked = capsys.readouterr().out
    cases = re.findall(r"^BLOCK must-pass reply case (t\d+)", blocked, flags=re.M)
    assert cases
    assert re.search(r"^Blocking rule: must-pass", body, flags=re.M), "write the line 'Blocking rule: must-pass ...'"
    named = re.search(r"^Blocking case: reply (t\d+)", body, flags=re.M)
    assert named and named.group(1) in cases, f"the blocked log names one of the cases {cases}"
    assert re.search(r"^INFO budget cost per 1,000 requests", body, flags=re.M) and re.search(r"^INFO budget p95 latency", body, flags=re.M), \
        "copy the two budget lines from the passing log"
