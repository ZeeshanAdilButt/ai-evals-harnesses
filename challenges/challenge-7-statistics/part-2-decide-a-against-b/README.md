# Challenge 7, part 2: decide A against B

Time: 60 minutes. Replay only. The goal: "Ship or not, and say why in one sentence." The rule and the tests are given; you write the paired interval and the verdict.

## Words you need

- **Paired**: A and B ran the same cases, so you compare them case by case, not as two separate scores.
- **Per-case difference**: B's five-trial mean minus A's for one case (+0.2 means B passed one more trial in five).
- **Paired bootstrap**: resample the per-case differences with replacement, take the mean, repeat 10,000 times with seed 7, read the 2.5th and 97.5th percentiles.
- **Verdict rule**: better if the whole 95% interval is above zero, worse if the whole interval is below zero, otherwise not proven.
- **Flip**: a case that passes under one variant and fails under the other on one trial. The sign test counts flips each way.
- **Sign test**: if B made no difference, each flip goes either way with probability one half. The exact two-sided p is twice the chance of the smaller count or fewer among x + y coin flips. 9 against 3 gives 0.146; 6 against 0 gives 0.031.

## Steps (the file is [decide.py](decide.py))

1. Why and safety rule (3 min): replay only, no key.
2. `python -m evalkit run --suite v1-triage --variant A --trials 5 --out runs/v7-A` and B, then `python -m evalkit stats paired runs/v7-A runs/v7-B` and read it (7 min).
3. `case_differences` (8 min): one number per case, B minus A.
4. `paired_bootstrap` (10 min): the shipped `resample_stats` with the mean as the statistic.
5. `verdict` (7 min): the rule above. Predict what the interval of the real data will say before you run it.
6. `sign_test` (10 min), then `python -m evalkit stats sign-test runs/v7-A runs/v7-B --trial 1` to compare.
7. The cases needed (5 min): chapter 7.7's formula n = ceil(max(7.84 (q - delta^2) / delta^2, 6 / q)), with q the share of cases whose five-trial means differ and delta the recorded difference. `results.md` shows the recorded values.
8. One sentence (5 min): "B is [better, worse, not proven better] than A on triage: [difference] points, 95% interval [lo, hi], [n] cases, five trials."
9. Run the tests and write `results.md` (5 min). Then the interview answer: "B scores higher than A. How do you decide whether to ship B?"

## Where each number comes from

- Grades: recorded triage outputs of A and B, canonical v1, five trials, category and urgent both right.
- Tolerance: your paired interval must be within 0.005 of `evalkit.stats.paired_bootstrap`; the verdict class must match.
- The sign test constructed inputs (9 and 3, 6 and 0) do not read the recordings.

## Tests

`pytest challenges/challenge-7-statistics/part-2-decide-a-against-b -q`: `test_diffs_are_per_case`, `test_paired_bootstrap_matches_within_tolerance`, `test_verdict_rule`, `test_sign_test_known_split`. The one-sentence answer is read by your mentor.

## Helper script

`python challenges/challenge-7-statistics/part-2-decide-a-against-b/cases_needed.py` applies chapter 7.7's formula to the recorded A and B (how many cases a difference of this size needs). It only reads the recordings. `python -m evalkit stats judge-interval runs/judge-test` (after challenge 5) gives the interval of the chosen judge's test TPR and TNR with the same `rate_interval` helper.
