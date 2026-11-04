# Challenge 5, part 2: compare judges on dev, report one on test

Time: 80 minutes, in two checkpoints. Replay only: every judge listed is recorded on the dev and test replies, `judge-eval` never calls a model, no key. "A judge is chosen on dev by a rule written before you look, and reported once on test."

## Words you need

- **Judge**: a model prompt that grades one reply pass or fail against the criterion. `v1` is the bare criterion, `v2` adds definitions and a fixed answer shape, `v3` has all five parts (criterion, definitions, labelled examples, a short reason before the verdict, the answer shape).
- **Builder id** `d{0,1}r{0,1}e{1,2,3}`: v3's parts switched on or off. `d` definitions, `r` reason before verdict, `e` which labelled example set. `d1r1e1` is the same prompt as v3 and the tool treats it as an alias, so you pick one of the other 11.
- **Fail is the positive class.** TPR is the share of expert fails the judge failed. TNR is the share of expert passes the judge passed. The counts are tp, fn, tn, fp.
- **Dev and test**: the expert-labelled replies you tune on (dev, 40 fails and 40 passes) and the ones you report once (test, the same sizes). Other chapters call them tuning and held-out.
- **The lock**: after the test report, `runs/judge-test.lock` holds the judge id. A second judge on test is refused.
- **Probe**: change one thing the verdict should not depend on (example order, padding, the judge's model family) and count the verdicts that move, read against a rerun of v3 with nothing changed.

## The idea from zero

If you pick the best of many judges on dev and then quote its dev numbers, you quote the lucky ones. So you write the rule first (TPR of at least 0.85, then the highest TNR; ties: the higher TPR, then the lower id), apply it on dev, and look at test once. A higher TNR cannot make up for a judge that misses too many fails.

## Steps

**Checkpoint 1: dev (about 45 min).**
1. Write `tpr_tnr(expert, judge)` and `choose_judge(dev_rows)` in [judge_rule.py](judge_rule.py) and run `test_tpr_tnr_fail_is_positive` and `test_choose_applies_floor_then_tnr`.
2. Run `python -m evalkit judge-eval --judge v1 --split dev`, then `v2`, `v3` and your builder id. Each writes `runs/judge-dev/<id>.json`. Read the counts and rates.
3. Run `python -m evalkit judge-eval --all --split dev` once to see all 14 recorded judges and how many pass the rule's first step.
4. Run `python -m evalkit choose`: it reads every file in `runs/judge-dev/`, applies your rule and writes `choice.json`. Write the dev table and `Choice by the rule: ID` in `results.md`.

**Checkpoint 2: test and probes (about 35 min).**
5. Run `python -m evalkit judge-eval --split test`. It runs once, for the choice. If you run it for another judge it refuses and names the lock; `python -m evalkit judge-eval --unlock` removes the lock and writes the reset into `results.md`.
6. Read the dev to test gap, then run `python -m evalkit judge-probes --judge J` for your choice. The rerun reference is measured once, on v3, and every probe is read against it; a count only a little above it is not a finding. For v1 and v2 the position probe reads "not applicable". Self-preference is recorded for v3 only.
7. Write the test counts, the three probe lines and the interview answer in `results.md`.

## Where each number comes from

- Verdicts: `recordings/judge/` (found by request key; trial 1). Labels: see part 1. The rerun is trial 2 of v3; the second-family judge is `v3-second.jsonl`.
- `judge-eval` reads the recordings and your `tpr_tnr`; `choose` reads your `choose_judge`. The shipped reference choice is in the facts as `m5.ref_choice_id`; yours is used in 7.5 and 11.2.
- `results.md` here is a stand-in learner's file made by `tools/make_results.py`.

## Tests

`pytest challenges/challenge-5-labels-and-judges/part-2-judge-comparison -q`. Rule tests: `test_tpr_tnr_fail_is_positive`, `test_choose_applies_floor_then_tnr`, `test_choice_is_allowed`, `test_lock_matches_choice`. Checkpoint tests: `test_checkpoint_1` (the section "Dev" lists v1, v2, v3 and your builder id with counts, and `choice.json` is the rule's choice over `runs/judge-dev/`), `test_checkpoint_2` (the lock matches `choice.json`, the test counts match the recording, three probe lines are each read against the rerun).
