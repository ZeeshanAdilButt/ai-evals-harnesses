# Challenge 9, part 1: build the gate script

Time: 60 minutes. Replay only: the gate reads run files, CI uses replay and needs no key. "One script decides whether a change can merge."

## Words you need

- **Gate**: a script that reads a run of the full suite and prints PASS, WARN or BLOCK lines. Exit code 0 when no line is a BLOCK (WARN lines are printed), 1 when one is, and 2 when the gate could not run (a gap in your code or missing margins). Both 1 and 2 turn the CI check red.
- **Case score and feature score**: a case's score is the mean of its five trial grades. A feature's score (triage, reply, agent) is the mean over its cases that are not quarantined.
- **Must-pass case**: a case tagged `must_pass: true` by the author (in canonical v1 for replies, in `datasets/agent_tasks.jsonl` for the tasks r27 and r28). Any must-pass case under 5 of 5 trials is a BLOCK, whatever the average says. The reply tags are the refund-window tickets that variant A passes on all five trials; the baseline must itself pass what the gate forbids others to break.
- **Floor**: the lowest feature score the team accepts (`gate.toml`).
- **Baseline**: variant A's results on the `full` suite, shipped in `baselines/full-A/`. A case is a **stable pass** when it passes 5 of 5 baseline trials; a case that passes 1 to 4 of 5 is **quarantined**: left out of the scores and the warnings, and listed.
- **Margin**: the noise a score may move without meaning anything: half the width of the case-level 95% bootstrap interval of the baseline, per feature. A feature drop larger than its margin is a BLOCK.
- **Budget**: cost per 1,000 requests (from tokens and `product/prices.toml`) and p95 latency (nearest rank over valid latencies), each with a limit in `gate.toml`.
- **Replay miss**: a request with no recording. `evalkit run` writes a `replay_miss` line and goes on; the gate blocks on it.

## The idea from zero

A person cannot read 1,800 trial results on every pull request. The gate turns four questions into numbers: did a case the team swore by break (must-pass)? did a whole feature fall under its floor? did it fall more than noise (margin)? did it get slower or dearer than the budget? A WARN says a stable case slipped while the feature stayed inside its noise: look, but do not stop the merge.

## Steps (the files are [gate.py](gate.py) and [smoke.py](smoke.py))

1. Why (5 min): read the safety line and the glossary.
2. Run `python -m evalkit gate runs/x --baseline baselines/full-A` with the starter (5 min): the first check raises `NotImplementedError`. Read why the test fails.
3. Write the checks in `gate.py` (32 min): `check_must_pass` and `check_floor` (10 min, a test each), `check_margin` (12 min), `check_budget` (6 min), `check_misses` (4 min). The nearest-rank p95 (`p95_ms`) and the quarantine filter (`quarantined_cases`) are shipped, so each function is one real decision.
4. Write `select_smoke(full_cases)` in `smoke.py` and run it (8 min): a subset of `full` with every must-pass case and four dev cases per category; no agent tasks.
5. Compute the margins once: `python -m evalkit gate --init-margin --baseline baselines/full-A` (writes them to `gate.toml`). Run the recorded variants `python -m evalkit run --suite full --variant ci-regression --out runs/ci-regression` (and `ci-harmless`), run the gate on each, read the exit codes (`echo $?`), write `results.md` (10 min).

## Where each number comes from

- Baseline and runs: `trials.jsonl` of `baselines/full-A` and of your runs; replay finds requests by key across the recording files, so triage and agent requests hit A's recordings and the patched replies hit the branch recordings.
- Floors, budgets, margins: `gate.toml`. Prices: `product/prices.toml`.
- Reply grading in `full`: the reply code checks of 4.5 plus asking for the order number when the ticket names none (`reply_facts`).
- `results.md` here is a stand-in learner's file made by `tools/make_results.py`.

## Tests

`pytest challenges/challenge-9-ship-gates/part-1-gate-script -q`. They fail on the starter. Passing means: the recorded regression run exits 1 and names a must-pass reply case; the harmless run exits 0 and prints the budget lines; a run with a `replay_miss` line exits 1 through `check_misses`; a fixture with a drop inside the margin exits 0 and prints WARN; a fixture over the cost budget exits 1; the 20-value list of 9.6 gives p95 1900; `test_smoke_is_subset_of_full_and_holds_every_must_pass_triage_and_reply_case` and `test_smoke_has_no_agent_tasks`.
