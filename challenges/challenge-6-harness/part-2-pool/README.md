# Challenge 6, part 2: the pool

Time: 50 minutes. Replay only: the pool sleeps a fraction of each recorded latency, it never opens a connection.

## Words you need

- **Worker**: one thread that takes the next call from a list when it is free.
- **Pool**: a fixed number of workers (`ThreadPoolExecutor(max_workers=w)`).
- **Future**: what `pool.submit(...)` returns; `future.result()` waits for the answer.
- **Timeout**: a limit on how long one call may take.
- **Lock**: lets one thread at a time through a piece of code.
- **Simulated latency**: `--simulate-latency 0.05` makes each replayed call sleep 5% of its recorded time.

## The idea from zero

400 calls one after another take 400 times the latency of one call. With 8 workers eight calls run at once, so the run is about eight times shorter (until a rate limit refuses calls). Two things must stay true. A slow call must not hold a worker forever: a Python thread cannot be stopped from outside, and `future.result(timeout=...)` only stops *waiting*, so the provider raises `TimeoutError` at its own limit and the worker is free again. And eight workers writing to one file must not cut each other's lines in two: a lock makes each line whole.

## Steps (the file is [pool.py](pool.py))

1. Read the skeleton and the failing tests in `test_pool.py` (5 min).
2. Fill `run_pool(tasks, workers, timeout_s)` (line 46, about 14 min). Each task is a function that takes `timeout_s`. Return one item per task, in order: its result, or the exception it raised.
3. Fill `SafeWriter.write` (line 30, 8 min).
4. Run with one worker and with eight:
   `python -m evalkit run --suite pool400 --variant A --workers 1 --simulate-latency 0.05`
   `python -m evalkit run --suite pool400 --variant A --workers 8 --simulate-latency 0.05`
   Add `--runner learner` to use yours.
5. Count the lines: 400 whole JSON lines in `runs/pool400-A/trials.jsonl` and in `runs/pool400-A-w8/trials.jsonl`.
6. Compare the measured time with the formula: calls x mean recorded latency x 0.05 / workers.
7. `pytest challenges/challenge-6-harness/part-2-pool -q`, then fill in `results.md`.

## Where each number comes from

- 400 calls: every ticket in `datasets/pool/tickets.jsonl`, trial 1.
- Mean recorded latency, 1.55 s: the mean of `latency_ms` of those 400 recorded lines (trial 1 is always sent directly, so its latency is valid).
- Formula: 400 x 1.55 x 0.05 = 31.0 s at one worker and 3.9 s at eight.
- The measured seconds in `results.md` are the formula plus the time to read prompts and write lines. They change from machine to machine; the line counts do not.
- [chart.svg](chart.svg) plots both against the number of workers (1, 2, 4, 8).
