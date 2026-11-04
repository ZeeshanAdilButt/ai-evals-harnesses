# Challenge 10, part 1: find the day it broke

Time: 100 minutes, in three checkpoints. Replay only: the judged sample is recorded; nothing here calls a model. "Somewhere in this week, something broke."

## Words you need

- **Trace**: one recorded request with its reply (and here the judge's verdict). The week has 3,500 tickets over seven days; about 30% are refund tickets, and judge v3 graded the reply to each of them.
- **Slice**: a cut of the traces by one field: tone, language or length.
- **Cell**: one day in one slice, with a sample size `n` and an observed pass rate.
- **Observed rate**: what the judge said. It is not the true pass rate: the judge has its own TPR and TNR (chapter 5).
- **Interval**: the 95% bootstrap interval of a cell's rate. A small cell has a wide one (10.5, 7.3).
- **Canary set**: 20 fixed tickets (10 of them refund tickets) replayed every day; the same inputs each day, so a change in score comes from the model or the service, not from traffic.

## The idea from zero

Average the whole week by day and a break in one slice barely shows: the other slices mix with the broken one and pull the day's rate back up. Cut the same data by slice and the broken cell stands out, but a cell with six replies swings by chance, so a rule for flagging must look at `n` and at the interval, not only the rate. Once you know the cell, you select its traces: they become test cases for the next dataset version.

## Steps (the files are [monitor.py](monitor.py) and [rule.py](rule.py))

**Checkpoint 1 (30 min): the week by day.**
1. Why: read the safety line and the glossary. Write down what you expect the chart to look like before you run anything.
2. Write `daily_rates(judged, group_by)` in `monitor.py`. Run `python -m evalkit monitor --day all`. Save a chart as `chart.svg` and write the table into `results.md`.

**Checkpoint 2 (35 min): day and slice with intervals.**
3. Run `python -m evalkit monitor --slice language` and `--slice tone`, and one day with `--day 5 --slice language`. Decide your rule (the numbers in `RULE`) and write `flag_cells(table, baseline_days, rule)`. Name the day and slice that broke in `results.md` ("Break: day D, slice S"). `python -m evalkit monitor --canary` shows the canary set for the same week (shipped, no gap).

**Checkpoint 3 (35 min): select, freeze, compare.**
4. Write `select_rule(trace)` in `rule.py`. Run `python -m evalkit select-traces --rule challenges/challenge-10-monitoring/part-1-find-the-day-it-broke/rule.py`, then `python -m evalkit dataset freeze --name my-v2` (note the hash) and `python -m evalkit dataset compare --name my-v2`.
5. Compare with the 40 additions of canonical dataset v2: which did you select that they did, which did you miss, which are extra. One line for each difference. Write `results.md` and your interview answer.

## Where each number comes from

- Tickets: `datasets/traffic/tickets.jsonl`; replies: `recordings/reply/` (variant A on days 1 to 4; on days 5 to 7 A-day5 for English tickets and A-day5-mixed for mixed-language ones, chosen by `evalkit.traffic.variant_for`); verdicts: `recordings/judge/v3.jsonl`, found by request key.
- The shipped answer (week table, flagged cells): `datasets/reference_grades/monitor.json`. Later chapters (11.2) use canonical v2, not your selection.
- `results.md` here is a stand-in learner's file made by `tools/make_results.py`.

## Tests

`pytest challenges/challenge-10-monitoring/part-1-find-the-day-it-broke -q`. `test_checkpoint_1`: your week table equals the shipped one within 0.005 and the chart is saved. `test_checkpoint_2`: a constructed week with a planted break is flagged on the right cell, a quiet week with small samples flags nothing, and on the recorded week your flagged cells equal the shipped ones. `test_checkpoint_3`: your rule selects only scrubbed refund traces of the flagged cells; the frozen file's hash matches its contents and holds only the selected ids; the comparison lines in `results.md` match.
