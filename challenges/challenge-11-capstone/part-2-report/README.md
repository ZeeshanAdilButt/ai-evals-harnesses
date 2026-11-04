# Challenge 11, part 2: write the ship or no-ship report

Time: 90 minutes, in three checkpoints. No model calls in this part. "A decision is only as good as its evidence on one page."

## Words you need

- **Report**: one to two pages that a person who was not in the room can act on.
- **Numbers block**: the fenced block at the end of `report.md` (three backticks and the word `numbers`, then `key: value` lines). `check_report.py` compares it with your part 1 results.
- **Verdict class**: for a claim about triage or reply, one of better, worse or not proven, always next to the paired difference and its 95% interval over cases.
- **Must-pass case**: a case the team swore by; the report lists each over five trials for A and the candidate.

## The idea from zero

Your reader has two minutes. The first section must say ship or no-ship in one sentence, with one sentence of reason. Every claim after it needs its evidence next to it: a difference with an interval, not two pass rates side by side; pass^k with "40 tasks, 5 trials" and no interval; the weakest slice, not only the average; cost and p95 against the budget; what the judge got wrong; and at least one limit. Write the sections in this order: 2 to 7, then 8, then 1 last.

## Steps (the file is `report.md`; start from [report.template.md](report.template.md))

1. Why: no model calls here. Open the template. Headings: 1 Decision, 2 The question and what changed, 3 Results by feature (3.1 Triage, 3.2 Reply, 3.3 Refund agent), 4 Results by slice, 5 Must-pass cases, 6 Judge agreement, 7 Cost and latency against the budget, 8 Limits and next steps, 9 Appendix.
2. Checkpoint 1 (30 min): fill sections 2 to 5 from `results.md` of part 1 and the numbers block for them. Run `pytest challenges/challenge-11-capstone/part-2-report -q -k checkpoint_1`.
3. Checkpoint 2 (30 min): sections 6 and 7: the test-split TPR and TNR with counts (fail is the positive class) and the judge id from 5.8, one line on the probes, cost and p95 against the budget.
4. Checkpoint 3 (30 min): section 8 (at least one limit and one next step), then section 1. After you write the decision, check it against three questions: did you state the result for the must-pass task across all five trials; did you state the weakest slice with its interval; did you compare cost and p95 with the budget? If not, rewrite it. Run `python challenges/challenge-11-capstone/part-2-report/check_report.py`; a mentor reads sections 1 and 8. Then write your interview answer: "State your decision in one sentence and defend it with the one result that matters most."

## Where each number comes from

- Sections 2 to 5 and 7: `../part-1-release-suite/summary.json` (your 11.2 run). Section 6: your 5.8 test report (`runs/judge-test.json`).
- The reference report in this repository is the author's answer key for the mentor; the learner's repository holds only the template.

## Tests

`pytest challenges/challenge-11-capstone/part-2-report -q`. They fail on the starter (the template is empty). `test_checkpoint_1`: headings 1 to 5; each number in the block for sections 2 to 5 equals the part 1 summary; every triage and reply claim has an interval; the agent lines give pass^k with 40 and 5 and no interval; each must-pass case lists its trials for A and the candidate. `test_checkpoint_2`: the judge section has counts and the cost section compares with the budget. `test_checkpoint_3`: all nine headings, a non-empty limits section, and a one-sentence decision line.
