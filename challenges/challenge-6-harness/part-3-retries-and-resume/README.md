# Challenge 6, part 3: retries and resume

Time: 60 minutes. Replay only: the fake provider adds failures to recorded outputs and never opens a connection. The tests pass their own `sleep` function, so no test waits.

## Words you need

- **Attempt**: one try of one call. A **trial** is one of the runs of a case; a trial may need several attempts.
- **Retryable**: an error a second try can fix. A rate limit (429), a timeout and a server error (5xx) are. A 400 (bad request) and an auth error are not: the same request fails the same way.
- **Backoff**: waiting longer after each failure so retries do not add to the load: 1, 2, 4, 8 seconds, never more than 30, never less than the `retry_after` the provider sends.
- **Resume**: after a crash, skip every (case, variant, trial) already in the results file and run the rest.
- **Fake provider**: `FakeProvider(seed=7)` returns the recorded outputs but fails some *first* attempts on purpose.

## The idea from zero

A run of 400 trials will meet failures. A good runner retries only what a retry can fix, waits longer each time, gives up after five attempts, and writes one line per trial (a retry replaces the failed attempt; it is not a new line). If the process dies at trial 312, the 312 finished lines are still in the file, and a resume runs only the missing 88.

The fake provider makes this testable. Counting first attempts from 0, attempt i gets a rate-limit error when i mod 5 = 4 (80 of 400) and a timeout when i mod 50 = 12 (8 of 400). Every retry succeeds. So a correct runner makes exactly 88 retries and 488 attempts, and the file has 400 lines.

## Steps (the file is [retries_resume.py](retries_resume.py))

1. Read the file and the failing tests in `test_retries.py` (5 min).
2. `is_retryable` (line 22, 5 min).
3. `backoff_delay` (line 37, 6 min). Check it gives 1, 2, 4, 8, 16, 30, 30.
4. `run_with_retries` (line 45, 12 min). It returns `(value, retried_errors)`.
5. `resume_skip` (line 65, 8 min).
6. Run with the fake provider and read the retries and attempts:
   `python -m evalkit run --suite pool400 --variant A --provider fake --workers 8 --backoff-scale 0.01 --out runs/p3`
   (`--backoff-scale 0.01` makes every wait 1% as long, for a quick run.)
7. Stop like a crash: add `--stop-after 312`. Count the lines in `runs/p3/trials.jsonl`: 312, and no `report.md`.
8. Resume: add `--resume`. Only the remaining 88 run.
9. `python -m evalkit check-runner`. If it fails, use `--runner reference` from chapter 7.5 on and say so in `results.md`.
10. Write the interview answer ("Walk me through what your runner does when a rate limit hits at trial 312") and fill in `results.md`.

## Where each number comes from

- 88 retries = 80 rate limits (i mod 5 = 4) + 8 timeouts (i mod 50 = 12) among 400 first attempts. 488 attempts = 400 + 88.
- 400 lines: one record per (case, variant, trial).
- 312 and 88: `--stop-after 312` ends the run after 312 trials; 400 minus 312 remain.
- A resumed run starts a new fake provider that counts first attempts from 0 again, so its retries differ from 88 (see `results.md`).
- `check-runner` runs every test of challenge 6 (26 at the pinned commit) against your three scripts.
