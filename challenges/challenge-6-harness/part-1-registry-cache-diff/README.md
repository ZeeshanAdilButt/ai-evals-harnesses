# Challenge 6, part 1: the registry, the cache and the diff

Time: 60 minutes. Replay only: a cache miss never calls a model.

## Words you need

- **Registry**: a dictionary of graders by name. A suite says `graders = ["schema", "match"]`; the runner looks each name up.
- **Decorator**: `@register_grader("exact")` above a function adds that function to the registry under the name `exact`.
- **Class**: groups some data with the methods that use it. `CachedProvider` holds the recordings of one feature and the hit and miss counts.
- **Exception**: an error with a name. `UnknownGrader` and `ReplayMiss` are raised when a name or a request is not known.
- **Cache hit / miss**: the request was recorded (hit) or never recorded (miss).
- **Diff**: the list of cases whose result changed between two runs.

## The idea from zero

A run is only as good as the record it keeps. The record starts with three small parts. The registry turns the names in a suite into functions. The cache answers a request from the recordings, and says "miss" when it was never recorded. The diff compares two records. The request key is a hash of the exact request, so changing one word of a prompt changes every key and every request misses. The run must keep going and write a `replay_miss` line for each trial, not stop.

## Steps (the file is [registry_cache_diff.py](registry_cache_diff.py))

1. Read the shells (6 min): `UnknownGrader` (line 22), `register_grader` (line 31), `CachedProvider` (line 57). The shells are finished except the marked gaps.
2. Run `python -m evalkit run --suite v1-triage --variant A --runner learner` before you start. It fails with `NotImplementedError: YOUR TURN` at the first gap. Without `--runner`, the command uses the reference runner while gaps are open.
3. Fill the registry: `register_grader` (line 33) and `get_grader` (line 41). The error text must be `no grader named <name>`.
4. Fill `CachedProvider.complete` (line 67): a hit returns the recorded line, a miss raises `ReplayMiss`, and both are counted.
5. Fill `diff_runs` (line 84). A case's score is the mean of its trial passes; list the cases whose score differs, with the direction.
6. Run A and B on `v1-triage`, then `python -m evalkit diff v1-triage-A v1-triage-B`.
7. Change one word of A's triage prompt (`product/prompts/triage_A.md`). Predict: how many trials hit? Run `v1-triage` again and read the `replay_miss` lines in `runs/v1-triage-A/trials.jsonl`. Put the file back.
8. `pytest challenges/challenge-6-harness/part-1-registry-cache-diff -q`.

## Where each number comes from

- 160 cases: canonical dataset v1, `datasets/canonical/v1/cases.jsonl`.
- 15 flips to pass and 10 to fail: `diff_runs` over the two `trials.jsonl` files; the triage `match` grader on trial 1.
- After the one-word change: 0 hits and 160 `replay_miss` lines, one per trial. The key is the SHA-256 of the whole request, so one changed word changes all of them.
- `results.md` in this folder was produced by a real replay run of these commands.
