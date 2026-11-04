# Challenge 11, part 1: run the release suite on the candidate

Time: 90 minutes, in three checkpoints. Replay only: no new calls. "Use everything you built, once."

## Words you need

- **Candidate**: the upgrade being reviewed: a cheaper, faster model (claude-haiku-5-5) with shortened prompts. **A** is the current model and prompts.
- **Release suite**: canonical dataset v2 (200 tickets for triage and reply, five trials each) and the 40 refund tasks (five trials). 72 of the 200 tickets are refund tickets (32 from v1 and the 40 added from the broken slice).
- **Paired difference**: for each case, candidate score minus A score; the mean of those and its 95% bootstrap interval over cases. Better if the whole interval is above zero, worse if below, otherwise not proven.
- **pass^k**: for one task with c passes in five trials, comb(c, k) / comb(5, k); the suite number is the mean over tasks.
- **Judge**: your 5.8 choice grades the refund replies. The recordings hold every judge that passed the 5.8 rule (dev TPR at least 0.85), on trial 1 of A's and the candidate's refund replies, and judge v3 on all five trials. A verdict that is not recorded yet is reported as "not recorded yet"; it is never guessed.

## The idea from zero

Eleven chapters gave you parts: graders, a judge you checked, a runner, statistics, a gate. This chapter plugs them into one config, runs A and the candidate over the same cases, and collects every number a ship decision needs: the differences with intervals, the slices, the must-pass cases over five trials, cost and latency against the budget. It does not decide; 11.3 does.

## Steps (the files are [release_config.toml](release_config.toml) and [run_release.py](run_release.py))

1. Why: read the safety line. Run `python -m evalkit check-runner`. If it passes, the suite uses your runner; if not, set `runner = "reference"` and say so in `results.md`.
2. Fill `release_config.toml` (the gaps): your graders from 4.5 and 8.6, your gate from 9.7, your judge from 5.8 (a builder id, or `v3` if the 5.8 test did not accept your choice), the runner, and the slices.
3. Run `python challenges/challenge-11-capstone/part-1-release-suite/run_release.py`. It runs A and the candidate on the release suite, runs your gate on the candidate against A, joins the judge verdicts and writes `summary.json`. Read the gate lines and the exit code: one tagged must-pass agent task passes 4 of 5 trials on the candidate, so the gate blocks, and the must-pass check names it.
4. Compute and write down the numbers the report needs (paired differences per feature and per slice with intervals, pass^1 and pass^4, cost per 1,000 requests, p95, the judge pass rate) in `results.md`. Do not decide yet.

## Where each number comes from

- Recordings: triage, reply and agent for A and the candidate; the judge verdicts in `recordings/judge/`. If a judge verdict is missing the script prints the "not recorded yet" line; `reference/results/capstone-recordings-needed.md` (reference repository) lists the exact recording commands.
- Cost: tokens in the recordings and `product/prices.toml` (list prices). p95: nearest rank over valid latencies. Budgets: `gate.toml`.
- `results.md` here is a stand-in learner's file made by `tools/make_results.py`.

## Tests

`pytest challenges/challenge-11-capstone/part-1-release-suite -q`. They fail on the starter (the config is unfilled). `test_checkpoint_1`: the config resolves, the judge is a recorded one with dev TPR at least 0.85, A and the candidate finish with no replay miss, and 72 refund replies are judged (skipped, with the "not recorded yet" line, while a recording is missing). `test_checkpoint_2`: the gate exit code is recorded and the paired differences per feature and per slice are present. `test_checkpoint_3`: agent pass^k, the must-pass table over five trials, cost and p95, and `summary.json`.
