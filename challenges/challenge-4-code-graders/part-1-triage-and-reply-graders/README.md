# Challenge 4, part 1: grade triage and the reply's facts

Time: 80 minutes, in three checkpoints. Graders are code and read recorded outputs, so there is no model call and no key. A grader that passes everything is the most dangerous code you own, so three test files fail first and you fix them one at a time.

## Words you need

- **Grader**: a function that reads one output (and what the case expects) and returns True or False.
- **Normalise**: make two strings that mean the same compare equal (lowercase, one space between words, straight quotes).
- **Schema check**: is the output the shape we asked for (one JSON object, a valid category, a true or false `urgent`)?
- **Whole-string match**: the output equals the expected JSON character for character. The model writes `{"category": "refund", "urgent": false}` with spaces; the compact expected JSON has none, so the number is 0.0%. The answer is right and the comparison is wrong. That is why graders compare fields.
- **Must contain / must not contain**: phrases a reply needs (`5 working days`, `today`) and phrases the policy forbids (`14 days`, `store credit`). From `datasets/reply_checks.jsonl`.
- **Refund days exact**: the reply writes the window as digits next to "day" (`7 days`, `7-day`). "A week" is the same period, but no number is written, so it fails; wording like that needs a judge or a person (chapter 1.4).
- **Tolerance**: money is compared within a cent (`grade_reply_amount`, shipped), never with `==`.
- **Audit**: a hand-written set of known-good and known-bad outputs. A grader must pass every good one and fail every bad one.
- **2 by 2 and 5 by 5 matrices**: rows are the true label, columns the predicted one. A row gives a recall (how many of the true ones it found), a column a precision (how many of its predictions were right).

## The idea from zero

You will grade A and B on canonical dataset v1 (160 cases) with your own code, and check your numbers against the reference. Triage and reply always run canonical v1, never your own dataset from chapter 3.

## Steps (the files are [graders.py](graders.py), [audit.py](audit.py) and [grade.py](grade.py))

Before you start: `python -m evalkit run --suite v1-triage --variant A` and the same for B (replay).

**Checkpoint 1: triage graders (about 25 min).**
1. Read the shipped helpers in [evalkit/graders/helpers.py](../../../evalkit/graders/helpers.py) and run `pytest challenges/challenge-4-code-graders -q`. Three test files fail. Read each failure (5 min).
2. Write `normalise` (8 min), `grade_triage_schema` (6 min), then `grade_triage_match` (6 min). One recorded output of A is wrapped in a code fence; the shipped `_parse` removes it. Rerun `test_triage_graders.py`.

**Checkpoint 2: reply graders (about 25 min).**
3. Write `grade_reply_contains` (9 min) and `grade_reply_refund_days` (8 min), following the shipped amount grader. Rerun `test_reply_graders.py`; read how `grade_reply_amount` uses a tolerance of 0.01 (8 min).

**Checkpoint 3: audit and matrices (about 30 min).**
4. Before the matrices, write down which category you expect to have the lowest recall for A.
5. Write your audit set in `audit_set` and `run_audit` (12 min): run `python challenges/challenge-4-code-graders/part-1-triage-and-reply-graders/audit.py` and fix every disagreement, in the grader or in the audit set.
6. `python challenges/challenge-4-code-graders/part-1-triage-and-reply-graders/grade.py --variant A`, then `--variant B`. Read the 2 by 2 urgent matrix and the 5 by 5 category matrix for each (10 min).
7. Name the weak class of each in one sentence, write the interview answer ("How do you know your code graders are right, and what do their numbers show?") and score it (8 min).

## Where each number comes from

- 160 cases: `datasets/canonical/v1/cases.jsonl`; outputs: trial 1 of the recordings in `recordings/triage/` and `recordings/reply/` (A and B, five trials recorded).
- The reply checks: `datasets/reply_checks.jsonl`, made by `tools/make_reply_checks.py` from the policy: 20 refund-window cases (also the must-pass cases), 13 cases that quote one charge, 40 with a required phrase, every case with the forbidden phrases.
- The reference values your numbers are compared with: the reference graders in `evalkit/graders/`; the facts are in `facts.json` under `m4.`.
- `results.md` in this folder is a stand-in learner's file produced by `tools/make_results.py`.

## Tests

`pytest challenges/challenge-4-code-graders -q`. `test_checkpoint_1` is `test_triage_graders.py` plus the rates in your results; `test_checkpoint_2` is `test_reply_graders.py`; `test_checkpoint_3` is `test_audit.py`, including `test_results_matrices`, which reads your matrices from `results.md` and compares them with the reference cell by cell, and checks that the weak class you name is the row with the lowest recall. If you stop, resume at the first checkpoint whose test fails. If your graders cannot pass, later chapters use the reference graders in `evalkit/graders/`.
