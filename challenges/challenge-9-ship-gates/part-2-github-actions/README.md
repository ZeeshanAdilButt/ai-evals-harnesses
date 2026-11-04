# Challenge 9, part 2: run the gate on GitHub Actions

Time: 75 minutes, in three checkpoints. Replay only: the workflow needs no secret and you add nothing to the repository's Actions secrets. "A gate that runs only on your laptop is not a gate."

## Words you need

- **Workflow**: a YAML file in `.github/workflows/` that tells GitHub what to run and when.
- **Trigger** (`on:`): the event that starts it. Here: a pull request into `main`.
- **Job and step**: a job runs on one machine; its steps run in order. A step that exits non-zero fails the job, and a failed required check blocks the merge.
- **Branch and pull request**: `ci/regression` and `ci/harmless` are branches made from your `main`; a pull request asks to merge one into `main`.
- **Patch**: a small text diff. Two patches in `ci/patches/` change only `product/prompts/reply_A.md`.

## The idea from zero

The gate of part 1 is a script. Make a machine run it for every pull request, and "can this merge?" stops depending on whether someone remembered. Two branches test it: the regression branch removes the sentence that tells the reply writer to ask for a photo or an order number (the gate must block it), the harmless one rewords the sign-off (the gate must pass it). On a branch variant A's prompt is the patched one, its requests have new keys, and replay finds them in the `ci-regression` or `ci-harmless` recordings, which ship in `main`.

## Steps

**Checkpoint 1 (25 min): the workflow.**
1. Check Actions are on for your copy (repository Settings, Actions, General); some accounts and organisations start copies with Actions off. Turn them on if needed.
2. Copy `ci/workflow-starter.yml` to `.github/workflows/gate.yml`. Fill the two gaps: the `on:` trigger (pull requests into `main`) and the gate step (`python -m evalkit gate runs/pr --baseline baselines/full-A`). The given steps check out, set up Python, install, and run `python -m evalkit run --suite full --variant A --out runs/pr`.
3. Run the tests for checkpoint 1, commit and push to `main`.

**Checkpoint 2 (20 min): the branches.**
4. Run `python -m evalkit make-ci-branches`. It needs a clean tree, makes `ci/regression` and `ci/harmless` from your current branch, applies one patch to each, commits, returns you to your branch and prints the two `git push` commands. It never pushes. Push both branches with the printed command.
5. Open two pull requests into `main` (browser or `gh pr create`). Write "pull request #N" for each in `results.md`.

**Checkpoint 3 (30 min): read the logs.**
6. Open the blocked run, find the gate step, name the rule and the case. Open the passing run and find the budget lines. Put both run links, the blocking rule and case, the budget lines and your interview answer in `results.md`.

## Where each number comes from

- The expected result is the check: the regression pull request is blocked by a must-pass reply case; the harmless one passes and its log shows the budget lines. Your two run links are the evidence. The recorded gate output is in part 1's `results.md`.
- `results.md` here is a stand-in file made by `tools/make_results.py`: its run links and pull request numbers are placeholders until the author runs CI in the reference repository.

## Tests

`pytest challenges/challenge-9-ship-gates/part-2-github-actions -q`. `test_checkpoint_1`: the workflow parses, triggers on `pull_request` for `main`, has no secret, runs the `run` step before the gate step, and the gate step names `baselines/full-A`. `test_checkpoint_2`: `make-ci-branches` works on a scratch repository (changes only files under `product/prompts/`, never pushes, refuses a dirty tree); your own `ci/` branches, if they exist, differ from `main` only there; `results.md` lists two pull requests. `test_checkpoint_3`: two run links, the blocking rule and case, the budget lines. A further test runs the gate in replay on the `ci-regression` and `ci-harmless` variants: 1 and 0.
