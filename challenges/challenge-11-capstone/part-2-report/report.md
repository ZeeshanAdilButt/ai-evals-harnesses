# Ship or no-ship: upgrading FreshMarket support to the candidate model

Write this report yourself, from the numbers of part 1 (`../part-1-release-suite/summary.json` and its `results.md`) and your 5.8 results. Fill sections 2 to 7 first, then 8, then 1 last. Then run `python challenges/challenge-11-capstone/part-2-report/check_report.py`.

## 1. Decision

Decision: (fill in: ship or no-ship, in one sentence)
Reason: (fill in: one sentence)

## 2. The question and what changed

(fill in: models, prompts, the suite, the dataset v2 hash, the recording dates)

## 3. Results by feature

### 3.1 Triage

(fill in: A, candidate, paired difference with its 95% interval, better, worse or not proven)

### 3.2 Reply

(fill in: A, candidate, paired difference with its 95% interval, better, worse or not proven)

### 3.3 Refund agent

(fill in: pass^1 and pass^4 for A and the candidate, "40 tasks, 5 trials", no interval)

## 4. Results by slice

(fill in: a table with n, A, candidate, difference and interval for each slice)

## 5. Must-pass cases

| case | A trials passed | candidate trials passed |
|---|---|---|
| (fill in) | (fill in) | (fill in) |

## 6. Judge agreement

(fill in: the judge id, the test-split counts TP, FN, TN, FP and TPR and TNR with fail as the positive class, one line on the probes)

## 7. Cost and latency against the budget

(fill in: cost per 1,000 requests and p95 for A and the candidate, the budget, inside or over)

## 8. Limits and next steps

- Limit: (fill in)
- Next: (fill in)

## 9. Appendix: commands, run ids, hashes

(fill in)

## The numbers block

The check script compares this block with your results. Keep it in step with the text above. Write a fraction as a decimal (0.891), and "not recorded yet" for a judge number that is not recorded.

```numbers
dataset_v2_hash: (fill in)
triage_pass_A: (fill in)
triage_pass_cand: (fill in)
triage_diff: (fill in)
triage_diff_lo: (fill in)
triage_diff_hi: (fill in)
triage_verdict: (fill in)
reply_pass_A: (fill in)
reply_pass_cand: (fill in)
reply_diff: (fill in)
reply_diff_lo: (fill in)
reply_diff_hi: (fill in)
reply_verdict: (fill in)
reply_weak_slice: (fill in)
reply_slice_n: (fill in)
reply_slice_diff: (fill in)
reply_slice_lo: (fill in)
reply_slice_hi: (fill in)
agent_pass1_A: (fill in)
agent_pass4_A: (fill in)
agent_pass1_cand: (fill in)
agent_pass4_cand: (fill in)
mustpass_n: (fill in)
mustpass_fail_task: (fill in)
mustpass_fail_trials: (fill in)
judge_id: (fill in)
judge_test_tp: (fill in)
judge_test_fn: (fill in)
judge_test_tn: (fill in)
judge_test_fp: (fill in)
judge_test_tpr: (fill in)
judge_test_tnr: (fill in)
reply_judged_n: (fill in)
reply_judge_pass_A: (fill in)
reply_judge_pass_cand: (fill in)
cost1k_A: (fill in)
cost1k_cand: (fill in)
p95_A_ms: (fill in)
p95_cand_ms: (fill in)
budget_cost_per_1k: (fill in)
budget_p95_ms: (fill in)
gate_exit_cand: (fill in)
```
