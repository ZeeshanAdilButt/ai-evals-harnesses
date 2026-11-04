# Challenge 7, part 1: intervals for A, B and a judge

Time: 45 minutes. Replay only: the stats code reads recorded outputs and run files; no model is called.

## Words you need

- **Case score**: the mean of a case's five trial grades (1 or 0 each). The case is the unit: five trials of one case are not five independent cases.
- **Standard error (SE)**: how much a mean would move if you drew another set of cases. SE = s / sqrt(n), where s is the sample standard deviation of the case scores (divide by n - 1; `sample_sd` is shipped) and n the number of cases. For scores that are all 0 or 1, s is close to sqrt(p(1 - p)), the formula of chapter 7.3; with five-trial means it is a little smaller.
- **95% interval**: p plus or minus 1.96 SE. A score cannot leave 0 to 1, so the interval is clipped, and the clip is noted.
- **Bootstrap**: draw n cases with replacement, take the mean, repeat 10,000 times with seed 7, read the 2.5th and 97.5th percentiles. The shipped `resample_stats` does the drawing; you write the statistic.
- **TPR and TNR of a judge**: with fail as the positive class, the share of expert fails the judge failed (TPR) and the share of expert passes it passed (TNR). Each is a rate out of its own replies, kept separate.
- **Rule of three**: with zero misses in n tries, the most the true miss rate could be is about 3 / n. A bootstrap of 41 of 41 gives 100% to 100%, which is not believable; the rule gives (1 - 3/41, 1) = (92.7%, 100%).

## The idea from zero

Every score you report gets an interval, and the judge's test numbers too. The intervals never change the judge you chose in 5.8. You compute A's and B's pass rates on canonical v1 (160 cases, five trials), put an interval on each two ways, and then do the same for rates like a judge's TPR.

## Steps (the file is [intervals.py](intervals.py))

1. Why and runner (3 min): the first line of `python -m evalkit run` says whether the learner runner or `--runner reference` runs. Both give the same numbers.
2. `python -m evalkit run --suite v1-triage --variant A --trials 5 --out runs/v7-A`, the same for B with `--out runs/v7-B` (4 min). The script reads the recordings directly, so it works without the run folders.
3. `se_interval` (10 min). `normal_interval` is the worked example of a clipped interval; you write p, SE and call it. Check with `python -m evalkit stats interval runs/v7-A`.
4. `bootstrap_interval` (9 min): seed 7, 10,000 resamples, through the shipped `resample_stats`; you write the statistic (the mean). Check with `python -m evalkit stats bootstrap runs/v7-A`.
5. `rate_interval` (11 min) for a judge's TPR and TNR: one verdict per reply, a pair back. The judge's real test numbers are made in chapter 5.8 (`python -m evalkit stats judge-interval runs/judge-test`); here you try the edges: 41 of 41 and 0 of 12.
6. Compare the unit with the wrong unit (4 min): `run_interval` uses one score per case; `wrong_unit_interval` treats the 800 grades as cases and gets an interval about 2.2 times too narrow. Run the tests.
7. Write `results.md` (4 min).

## Where each number comes from

- Grades: the recorded triage outputs of A and B on canonical v1, trials 1 to 5, graded by category and urgent both right (the `match` grader). 160 cases.
- The constructed counts (41 of 41, 0 of 12) are made up to show the edges.
- The tests compare with `evalkit.stats`, within 0.005 (half a point).
- `results.md` is produced by `tools/make_results.py`; the chart shows the half-width of the interval against the number of cases at A's pass rate.

## Tests

`pytest challenges/challenge-7-statistics/part-1-intervals -q`. `test_se_matches_evalkit_stats`, `test_bootstrap_matches_within_tolerance`, `test_rate_interval_edges_return_pairs` and `test_unit_is_case_not_grade` fail until your functions are written.
