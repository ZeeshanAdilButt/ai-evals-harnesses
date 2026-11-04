# Challenge 1, part 1: set up, run your first eval, and break it

Time: 80 minutes, in three checkpoints. Replay only: nothing here calls a model. A live call needs `--live`, a key you set yourself, a printed cost and a `y`, and this runner does not offer it.

## Words you need

- **Case**: one input with the answer we expect (a support ticket and its right category).
- **Variant**: one version of the product. `A` is the current prompt, `B` is a rewritten prompt.
- **Trial**: one run of one case. This suite uses trial 1 only.
- **Grader**: a check that says pass or fail for one output. Here: `schema` (valid JSON with the right fields) and `match` (right category and right urgent flag).
- **Replay**: answers come from `recordings/`, saved from real model calls. The same request always gets the same answer.
- **Flip**: a case whose result differs between two variants. It "flips to pass" if it fails under A and passes under B.
- **Run id**: the name of a run folder in `runs/`. `m1-triage-A` is suite `m1-triage`, variant `A`.

## The idea from zero

A teammate changes the prompt and says "it is better". You cannot see that from one reply. You run the same ten cases through both versions, grade every output the same way, and compare. The pass counts can be equal while the cases that pass are different, so you also list the cases that flipped. Those are the cases to read.

## Steps

**Checkpoint 1: setup (about 25 min).** Copy the template, clone it, make a virtual environment, install. Then:

1. `python -m evalkit doctor`. Four lines must start with `OK`: Python 3.11 or newer, packages, Git, replay.
2. `pytest challenges/challenge-1-first-eval -q`. It fails. Before you run it, write down which line of the failure will say what is empty. (It is the `AssertionError` line from `test_flipped_list`.)
3. Create a branch, push it, open a draft pull request. Write the branch name in `results.md`.

**Checkpoint 2: run A (about 20 min).**

4. `python -m evalkit run --suite m1-triage --variant A`. It prints the run id and a line `pass N of 10`.
5. Open `runs/m1-triage-A/report.md`: cases, passes, failures by grader. Write the run id and the pass count in `results.md`.

**Checkpoint 3: break it (about 35 min).**

6. `python -m evalkit run --suite m1-triage --variant B`.
7. Guess how many cases flipped, then `python -m evalkit diff m1-triage-A m1-triage-B`. The last column says which cases flipped and which way.
8. Read the three finished functions in [first_eval.py](first_eval.py): `case_passed` (line 19), `flipped_cases` (line 24), `flip_direction` (line 31). Say in one sentence what each returns. Run the file to check your reading.
9. Write `my_flips.json`: for each flipped case its id, the direction (`to_pass` or `to_fail`) and `grader_type`, the kind of grader that can say whether the flip is good or bad: `code`, `judge` or `person`.
10. Answer the interview question in `results.md` under `### Interview answer`: "A teammate rewrote the triage prompt and says it is better. How do you check?" Use four parts: claim, reason, cost, next.

You write no code in this part. Your work is `my_flips.json` and `results.md`.

## Where each number comes from

- `pass N of 10`: the count of `passed: true` lines in `runs/<id>/trials.jsonl`. A trial passes when every grader in the suite says yes.
- The ten cases: `suites/m1-triage.toml`, taken from canonical dataset v1.
- Every output in the diff table is a recorded model output; the "expected" column is the case's label in the dataset.
- A and B each pass 6 of 10, and 4 cases flip, 2 each way. That is why equal counts hide change.
- `results.md` in this folder is the author's file from a real replay run.

## Tests

`pytest challenges/challenge-1-first-eval -q`. `test_checkpoint_1` checks the four `OK` lines and your branch name. `test_checkpoint_2` checks the run id and the pass count. `test_checkpoint_3` runs `test_flipped_list` (your `my_flips.json` against the recordings) and checks that your answer is not empty. If you stop, resume at the first checkpoint whose test fails.
