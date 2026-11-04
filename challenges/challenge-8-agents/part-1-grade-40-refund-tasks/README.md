# Challenge 8, part 1: grade 40 refund tasks, five trials each

Time: 100 minutes, in three checkpoints. Replay only: the 400 agent trials (40 tasks, five trials, variants A and B) are already recorded; you grade them, no key and no new calls. "The message looked fine. Check the ledger."

## Words you need

- **Task**: one refund request with an order, the expected final state (`expected_state`: refunds and escalations), forbidden calls (`never`), ordered pairs of calls (`before`), a `step_budget`, and a scripted customer.
- **Trial**: one run of the agent on a task. `final_state` is what the store holds at the end (the ledger of refunds, the escalations); `trajectory` is every tool call in order.
- **State grader**: checks the end result in the ledger. The shipped `grade_final_state` applies four checks: refund count, refund orders, refund amounts within 0.01, escalations.
- **Trajectory grader**: checks how the agent got there, by rule: R1 a `never` rule (no refund where none is allowed, no second refund, no refund over the order total), R2 a `before` pair (look up the order before refunding), R3 the step budget.
- **pass^k**: for one task with c passes in n = 5 trials, pass^k = comb(c, k) / comb(5, k): the chance that k trials picked from the five all pass. The suite number is the mean over tasks. pass^1 is the average pass rate; pass^4 asks for four in a row.
- **First failing step**: the first tool call that breaks a rule or leaves the wrong state.
- **Simulator failure**: the scripted customer gave up (`gives_up_after`) while the agent's last move was allowed by the rules. The agent is not at fault; the test double is.

## The idea from zero

A final message can look fine while the ledger is wrong, or the ledger can be right after a path the rules forbid (two refunds, one reversed later). So you grade both: the state, which is given to you as a worked grader, and the trajectory, which you write. Then you look at the failures one by one, because some are the agent's and some are the simulator's.

## Steps (the file is [agent_grade.py](agent_grade.py))

**Checkpoint 1: the state table (about 30 min).**
1. Why (5 min): read the safety line, the ledger and `grade_final_state`.
2. The tool loop is already replayed and saved in `recordings/agent-runs/` (`python -m evalkit run --suite agent40 --variant A` grades the same recorded loops with the shipped reference graders). Run `python challenges/challenge-8-agents/part-1-grade-40-refund-tasks/agent_grade.py`: it grades both variants and writes `runs/agent40-A` and `runs/agent40-B` in the run format (40 tasks x 5 trials = 200 trials each).
3. Before you run it, write down how many tasks you expect to fail on state alone. Then read the table of state passes per task in your `results.md` (25 min).

**Checkpoint 2: the trajectory grader (about 35 min).**
4. Write `grade_trajectory`. Run the audit tests: a good trial that looks things up in a different order passes; the double refund fails with R1 named. Write the two audit lines in `results.md`.

**Checkpoint 3: pass^k, first failing step, the simulator (about 35 min).**
5. Call the shipped `pass_hat_k` and read it; check one task by hand against chapter 8.4. Compute pass^1 and pass^4 per variant from the five trials per task and check with `python -m evalkit stats passk runs/agent40-A --k 1` and `--k 4`.
6. Call the shipped `first_failing_step_of` on three failed trials and read each (a rule broken, or a wrong end state).
7. Call the shipped `is_simulator_failure` over the failed trials. Chapter 8.5 showed one planted simulator failure (r11). Find the other one by reading its transcript (the trajectory and the final message) and label its failed trials `simulator`; every other failure is `agent`.
8. Write `results.md` and the interview answer: "Your refund agent passes most trials. Why is that not enough to ship it?"

## Where each number comes from

- 40 tasks: `datasets/agent_tasks.jsonl`; orders: `datasets/agent/orders.json`; trials: `recordings/agent-runs/A.jsonl` and `B.jsonl` (200 each). The counts 40 and 5 are fixed.
- The reference grades (a per-trial file, the canonical twin): `datasets/reference_grades/agent.jsonl`. After the part, compare yours with it and explain each difference in one line. Your grader is used in the capstone.
- pass^k: the shipped `evalkit.stats.pass_hat_k(c, n, k)`, averaged over the 40 tasks.
- `results.md` here is a stand-in learner's file produced by `tools/make_results.py`.

## Tests

`pytest challenges/challenge-8-agents -q`. `test_checkpoint_1` needs only the shipped state grader and your state table in `results.md`. `test_checkpoint_2` and `test_checkpoint_3` fail until `grade_trajectory` is written. CP2: a good trial with a different tool order passes, the double refund fails with R1 named, each rule is named, and your grader agrees with the reference on all 400 trials. CP3: pass^k values, your pass^1 and pass^4 within 0.005, per-task grades byte stable on a re-run, and the failed trials of the planted simulator task labelled `simulator` and no other failure.

## Helper scripts (run from anywhere; they read the recordings and the shipped helpers)

- `python challenges/challenge-8-agents/part-1-grade-40-refund-tasks/state_table.py` prints the state table of variant A (checkpoint 1; it uses only the shipped state grader).
- `python .../audit.py` grades two constructed trials of task r01 with your `grade_trajectory` (checkpoint 2).
- `python .../read_failures.py` shows pass^k by hand for two tasks, the first failing step of three trials, and the failed trials where the customer ended the task; add `--table` to print the label table (checkpoint 3).
- `python -m evalkit run --suite agent40 --variant A` grades the recorded tool loops with the shipped reference graders and writes a run in the run format (`runs/agent40-A`); `python -m evalkit diff agent40-A agent40-B` lists the tasks that flipped with the tools each variant called.
