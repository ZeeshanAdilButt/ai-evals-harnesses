"""Run the real commands of challenges 1 to 11 in replay and write each part's results.md,
the charts, and the facts (merged into facts.json). Run from the repo root:
    .venv\\Scripts\\python.exe tools/make_results.py
Everything except the measured seconds in part 2 is byte-stable.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit import engine  # noqa: E402
from evalkit.replay import Store  # noqa: E402
from evalkit.runner_learner import load_impl  # noqa: E402
from evalkit.suites import RUNS, load_cases, load_suite, read_jsonl  # noqa: E402
from product import triage  # noqa: E402

C1 = ROOT / "challenges/challenge-1-first-eval/part-1-setup-and-first-run"
C6 = ROOT / "challenges/challenge-6-harness"
facts = {}


def cli(*args, expect=0):
    """Run `python -m evalkit ...`; return the text a learner sees (absolute paths made relative)."""
    p = subprocess.run([sys.executable, "-m", "evalkit", *args], capture_output=True, text=True, cwd=ROOT, encoding="utf-8")
    assert p.returncode == expect, (args, p.returncode, p.stdout, p.stderr)
    text = (p.stdout + p.stderr).replace(str(ROOT) + "\\", "").replace("\\", "/")
    return text.strip("\n")


def drop_elapsed(text):
    return "\n".join(l for l in text.splitlines() if not (l.startswith("workers ") and "elapsed" in l))


def block(cmd, out):
    return f"```\n$ python -m evalkit {cmd}\n{out}\n```\n"


def write(path, text):
    assert chr(0x2014) not in text and chr(0x2013) not in text
    Path(path).write_text(text, encoding="utf-8")


# ---------------- challenge 1 ----------------
doctor = cli("doctor")
facts["m1.doctor_output"] = doctor.splitlines()
outs = {}
for v in "AB":
    outs[v] = drop_elapsed(cli("run", "--suite", "m1-triage", "--variant", v))
diff = cli("diff", "m1-triage-A", "m1-triage-B")
ra = read_jsonl(RUNS / "m1-triage-A/trials.jsonl")
rb = read_jsonl(RUNS / "m1-triage-B/trials.jsonl")
pa, pb = sum(r["passed"] for r in ra), sum(r["passed"] for r in rb)
pa_by = {r["case_id"]: r["passed"] for r in ra}
pb_by = {r["case_id"]: r["passed"] for r in rb}
flips = [c for c in pa_by if pa_by[c] != pb_by[c]]
to_pass = [c for c in flips if pb_by[c]]
to_fail = [c for c in flips if pa_by[c]]
mf = json.loads((C1 / "my_flips.json").read_text(encoding="utf-8"))
suite = load_suite("m1-triage")
facts.update({"m1.suite_size": len(ra), "m1.pass_a": pa, "m1.pass_b": pb, "m1.flipped_cases": len(flips),
              "m1.flips_to_pass": len(to_pass), "m1.flips_to_fail": len(to_fail), "m1.flipped_ids": sorted(flips),
              "m1.flip_grader_types": {f["case_id"]: f["grader_type"] for f in mf},
              "m1.demo_case_ids": suite["part"][0]["cases"], "m1.demo_pass_a": pa, "m1.demo_pass_b": pb, "m1.demo_flips": len(flips),
              "m1.cost_code_check": 0})
answer = (
    "Claim: I would not trust the claim yet. I run the old and the new prompt on the same fixed cases with the same graders and read the cases that changed.\n\n"
    "Reason: pass counts can hide movement. On the ten cases A and B both pass 6, yet 4 cases flipped, 2 each way, so equal counts do not mean equal behaviour. "
    "The diff shows which cases changed and whether each change is right against the label.\n\n"
    "Cost: ten cases and one trial each is a small, noisy sample, and a code check only covers what the label says. A real answer needs more cases and several trials.\n\n"
    "Next: run the full canonical set with five trials, look at the flipped cases by hand, and only then decide."
)
write(C1 / "results.md", f"""# Challenge 1, part 1: results

Produced by `tools/make_results.py` from a real replay run. Replay only: no model was called.

## Checkpoint 1: setup

Branch: learner/first-eval

The four lines `python -m evalkit doctor` printed:

{block("doctor", doctor)}
## Checkpoint 2: run A

{block("run --suite m1-triage --variant A", outs["A"])}
Run id: m1-triage-A
Passed: {pa} of {len(ra)}

## Checkpoint 3: run B, diff, flips and your answer

{block("run --suite m1-triage --variant B", outs["B"])}
Run id: m1-triage-B
Passed: {pb} of {len(rb)}

{block("diff m1-triage-A m1-triage-B", diff)}
Flipped cases: {len(flips)} ({len(to_pass)} to pass under B, {len(to_fail)} to fail under B): {", ".join(sorted(flips))}

The grader that says whether each flip is good or bad: code for all four (the case has a label, and a code check compares the output with it).

### Interview answer

Question: A teammate rewrote the triage prompt and says it is better. How do you check?

{answer}
""")

# ---------------- challenge 6, part 1 ----------------
impl1 = load_impl(learner=["part-1-registry-cache-diff"])
v1a = drop_elapsed(cli("run", "--suite", "v1-triage", "--variant", "A"))
v1b = drop_elapsed(cli("run", "--suite", "v1-triage", "--variant", "B"))
d6 = cli("diff", "v1-triage-A", "v1-triage-B")
a6, b6 = read_jsonl(RUNS / "v1-triage-A/trials.jsonl"), read_jsonl(RUNS / "v1-triage-B/trials.jsonl")
rows = impl1.diff_runs(a6, b6)
up = sum(r["direction"] == "to_pass" for r in rows)
orig = (triage.PRODUCT / triage.VARIANTS["A"]["triage_prompt"]).read_text(encoding="utf-8")
tmp = Path(tempfile.mkdtemp()) / "triage_A_changed.md"
tmp.write_text(orig.rstrip() + " Please.\n", encoding="utf-8")
saved = triage.VARIANTS["A"]["triage_prompt"]
triage.VARIANTS["A"]["triage_prompt"] = str(tmp)
try:
    changed = engine.run_suite("v1-triage", "A", impl=impl1, out=RUNS / "v1-triage-A-oneword")
finally:
    triage.VARIANTS["A"]["triage_prompt"] = saved
miss_lines = [r for r in read_jsonl(RUNS / "v1-triage-A-oneword/trials.jsonl") if r["status"] == "replay_miss"]
first_miss = miss_lines[0]
miss_line = json.dumps({k: first_miss[k] for k in ("case_id", "status", "error")})
facts.update({"m6.suite_cases": len({r["case_id"] for r in a6}), "m6.flips_to_pass": up, "m6.flips_to_fail": len(rows) - up,
              "m6.miss_line": first_miss["error"], "m6.changed_word_hits": changed["ok"], "m6.changed_word_miss_lines": len(miss_lines)})
write(C6 / "part-1-registry-cache-diff/results.md", f"""# Challenge 6, part 1: results

Produced by `tools/make_results.py` (replay only, the registry, cache and diff from `registry_cache_diff.py`).

## Run A and B on v1-triage

{block("run --suite v1-triage --variant A", v1a)}
{block("run --suite v1-triage --variant B", v1b)}
## Diff

{block("diff v1-triage-A v1-triage-B", d6)}
Cases: {facts["m6.suite_cases"]}. Flipped: {len(rows)} ({up} to pass under B, {len(rows) - up} to fail under B).

## One word changed in A's system prompt

I appended one word ("Please.") to the triage prompt of A for one run and ran `v1-triage`; the file on disk was not touched.

- trials in the suite: {changed["records"]}
- cache hits: {changed["ok"]}
- `replay_miss` lines in `trials.jsonl`: {len(miss_lines)}
- first miss line (case, status, error): `{miss_line}`

The run did not stop at the first miss and did not call a model: every trial got a `replay_miss` line, and the summary counts them.
""")

# ---------------- challenge 6, part 2 ----------------
store = Store.load("triage")
cases = load_cases(load_suite("pool400")["part"][0])
lat = [store.lookup(triage.build_request("A", c["text"])["key"], 1)["latency_ms"] for c in cases]
mean_s = sum(lat) / len(lat) / 1000
pool_out, measured = {}, {}
for w in (1, 2, 4, 8):
    text = cli("run", "--suite", "pool400", "--variant", "A", "--workers", str(w), "--simulate-latency", "0.05")
    rid = f"pool400-A-w{w}" if w > 1 else "pool400-A"
    whole = len(read_jsonl(RUNS / rid / "trials.jsonl"))
    meta = json.loads((RUNS / rid / "meta.json").read_text(encoding="utf-8"))
    measured[w] = meta["elapsed_s"]
    pool_out[w] = (drop_elapsed(text), whole)
est = {w: round(len(cases) * mean_s * 0.05 / w, 1) for w in (1, 2, 4, 8)}
facts.update({"m6.pool_calls": len(cases), "m6.mean_latency_s": round(mean_s, 3), "m6.est_seconds_w1": est[1], "m6.est_seconds_w8": est[8],
              "m6.measured_seconds_w1": round(measured[1], 1), "m6.measured_seconds_w8": round(measured[8], 1)})
rows_md = "\n".join(f"| {w} | {pool_out[w][1]} | {est[w]} | {measured[w]:.1f} |" for w in (1, 2, 4, 8))
write(C6 / "part-2-pool/results.md", f"""# Challenge 6, part 2: results

Produced by `tools/make_results.py` (replay only; the calls sleep 0.05 times their recorded latency, no network).

## The runs

{block("run --suite pool400 --variant A --workers 1 --simulate-latency 0.05", pool_out[1][0])}
{block("run --suite pool400 --variant A --workers 8 --simulate-latency 0.05", pool_out[8][0])}
## Numbers

- calls: {len(cases)}
- mean recorded latency of trial 1: {mean_s:.3f} s
- formula, model time = calls x mean latency x 0.05 / workers: {est[1]} s at 1 worker, {est[8]} s at 8

| workers | whole JSON lines | formula (s) | measured (s) |
|---|---|---|---|
{rows_md}

The measured time is the formula plus the cost of reading prompts and writing lines, so it runs a little above it and changes from machine to machine. The line counts do not.

![run time against workers](chart.svg)
""")
W, H = 480, 280
mx = max(max(est.values()), max(measured.values())) * 1.1


def pt(w, y):
    x = 60 + (w - 1) / 7 * 380
    return f"{x:.0f},{H - 40 - y / mx * (H - 80):.0f}"


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="sans-serif" font-size="12">',
       f'<rect width="{W}" height="{H}" fill="white"/>',
       f'<line x1="60" y1="{H-40}" x2="440" y2="{H-40}" stroke="black"/><line x1="60" y1="40" x2="60" y2="{H-40}" stroke="black"/>',
       f'<polyline fill="none" stroke="black" stroke-width="2" points="{" ".join(pt(w, est[w]) for w in (1, 2, 4, 8))}"/>',
       f'<polyline fill="none" stroke="gray" stroke-width="2" stroke-dasharray="5 4" points="{" ".join(pt(w, measured[w]) for w in (1, 2, 4, 8))}"/>',
       f'<text x="{W/2}" y="20" text-anchor="middle">Run time of pool400 (0.05 x recorded latency) against workers</text>',
       f'<text x="250" y="{H-10}" text-anchor="middle">workers</text><text x="14" y="150" transform="rotate(-90 14 150)" text-anchor="middle">seconds</text>',
       '<text x="300" y="60">solid: formula</text><text x="300" y="76" fill="gray">dashed: measured</text>']
for w in (1, 2, 4, 8):
    x = 60 + (w - 1) / 7 * 380
    svg.append(f'<text x="{x:.0f}" y="{H-24}" text-anchor="middle">{w}</text>')
svg.append("</svg>")
write(C6 / "part-2-pool/chart.svg", "\n".join(svg) + "\n")

# ---------------- challenge 6, part 3 ----------------
common = ["--suite", "pool400", "--variant", "A", "--provider", "fake", "--workers", "8", "--backoff-scale", "0.01", "--out", "runs/p3"]
shutil.rmtree(ROOT / "runs/p3", ignore_errors=True)
full_s = drop_elapsed(cli("run", *common))
fs = json.loads((ROOT / "runs/p3/meta.json").read_text(encoding="utf-8"))["summary"]
shutil.rmtree(ROOT / "runs/p3", ignore_errors=True)
crash = cli("run", *common, "--stop-after", "312", expect=1)
done = len(read_jsonl(ROOT / "runs/p3/trials.jsonl"))
res = drop_elapsed(cli("run", *common, "--resume"))
final = read_jsonl(ROOT / "runs/p3/trials.jsonl")
keys = {(r["case_id"], r["variant"], r["trial"]) for r in final}
chk = cli("check-runner")
n_tests = int(re.search(r"(\d+) tests passed", chk).group(1))
facts.update({"m6.fake_retries": fs["retries"], "m6.fake_timeouts": fs["retry_kinds"].get("timeout", 0),
              "m6.fake_rate_limits": fs["retry_kinds"].get("rate_limit", 0), "m6.fake_attempts": fs["attempts"],
              "m6.fake_lines": fs["records"], "m6.resume_done_before_stop": done, "m6.resume_remaining": 400 - done,
              "m6.resume_final_lines": len(final), "m6.resume_unique_keys": len(keys), "m6.check_runner_tests": n_tests})
write(C6 / "part-3-retries-and-resume/results.md", f"""# Challenge 6, part 3: results

Produced by `tools/make_results.py` (replay only; the fake provider adds failures to recorded outputs and opens no connection).
The commands use `--workers 8 --backoff-scale 0.01 --out runs/p3` so that the waits (1, 2, 4 ... seconds) take 1% of their real time; the waits are still computed by `backoff_delay`.

## Fake provider, 400 trials

{block("run --suite pool400 --variant A --provider fake --workers 8 --backoff-scale 0.01 --out runs/p3", full_s)}
- trials (lines in the results file): {fs["records"]}
- attempts: {fs["attempts"]} = {fs["records"]} trials + {fs["retries"]} retries
- retries: {fs["retries"]} = {fs["retry_kinds"].get("rate_limit", 0)} rate limits + {fs["retry_kinds"].get("timeout", 0)} timeouts

## Stop after 312, then resume

{block("run ... --stop-after 312", crash)}
Lines in `trials.jsonl` after the stop: {done}. No `report.md` was written.

{block("run ... --resume", res)}
- trials run by the resume: {400 - done}
- lines at the end: {len(final)}, distinct (case, variant, trial) keys: {len(keys)}

The resume starts a new fake provider, so its first attempts are counted from 0 again; the retries of a stopped and resumed run therefore differ from the {fs["retries"]} of an unbroken run.

## check-runner

{block("check-runner", chk)}
""")

# ---------------- challenges 2, 3, 4, 7 and 8 (tools/make_results_c2_8.py) ----------------
import make_results_c2_8  # noqa: E402

facts.update(make_results_c2_8.run(cli, write, block))

import make_results_c5_11  # noqa: E402

facts.update(make_results_c5_11.run(cli, write, block))

fj = ROOT / "facts.json"
allf = json.loads(fj.read_text(encoding="utf-8")) if fj.exists() else {}
allf.update(facts)
fj.write_text(json.dumps(allf, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(facts, indent=1))
