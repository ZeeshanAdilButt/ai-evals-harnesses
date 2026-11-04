# Challenge 2, part 2: build your taxonomy and three criteria

Time: 60 minutes. No model calls and no AI assistant: your notes, your groups, your criteria. The ranking function is shipped; you read it, you do not write it.

## Words you need

- **Failure mode**: a named kind of failure that more than one trace shows ("States a fact it cannot support").
- **Top mode**: the first failure in a reply, one per trace. Every trace gets exactly one, so the counts add up to 60. A trace with no failure gets the mode `No failure found`; it is counted but not ranked.
- **Cost weight**: 1 (minor), 2 (the customer is misled or annoyed) or 3 (the customer could be harmed or lose money). You choose it.
- **Score**: count x cost weight. `rank_modes` in [evalkit/taxonomy.py](../../../evalkit/taxonomy.py) sorts by it, ties by name, and keeps both columns so you can see why a rare, costly mode can outrank a common, cheap one.
- **Saturation**: reading in order, the point after which new traces stop adding new modes. `saturation_at` is the position of the trace where your last new mode first appeared.
- **Criterion**: one yes or no question about one output, with a pass example and a fail example.

## The idea from zero

You have 30 notes of your own (part 1) and 30 the author wrote (`datasets/traces/author_notes.jsonl`, tr31 to tr60). Put them side by side, group the 60 into modes, count, and weigh. The top few modes tell you what to measure first. Then write one criterion for each of three modes so that two people grade the same reply the same way.

## Steps

1. Read the author's 30 notes next to yours (7 min).
2. Group all 60 notes into modes. Give each trace exactly one top mode (14 min).
3. Write `my_taxonomy.yaml` (10 min). It is a plain text file of names and values:

   ```
   saturation_at: 27
   modes:
     States a fact it cannot support: {weight: 3, example: tr52}
     No failure found: {weight: 0, example: tr02}
   traces:
     tr01: States a fact it cannot support
     tr02: No failure found
   ```

   `traces:` lists all 60 trace ids in the order you read them (your 30 first), each with its one mode. Run `python -m evalkit taxonomy-check challenges/challenge-2-error-analysis/part-2-taxonomy-and-criteria/my_taxonomy.yaml`. If you list 58 traces it fails: the counts are the evidence, and a trace without a mode is a hole in them. Read the ranking it prints.
4. Mark saturation (4 min): going through the traces in reading order, find the trace where your own notes last added a new mode and write its position (1 to 60) as `saturation_at`. Say in one line how it compares with the author's.
5. Write `criteria/v1.md` (14 min): three criteria, each under a `## ` heading with `Question:`, `Pass example:` and `Fail example:` lines. Run `python -m evalkit criteria-check criteria/v1.md`. The checklist: one question, answerable pass or fail, one pass and one fail example, no vague word such as "good" or "helpful".
6. Compare (6 min): `python -m evalkit criteria-check criteria/v1.md --compare criteria/` lists your criteria against `criteria/shipped.md`. Write one line for each difference in `results.md`, and why you kept your version. Say which shipped criterion module 5 will grade (criterion 1, the refund policy). The shipped criteria, not yours, are used later, so an unusual choice never breaks module 5.
7. Write the interview answer and score yourself with the rubric (5 min).

`python challenges/challenge-2-error-analysis/part-2-taxonomy-and-criteria/taxonomy_report.py` prints your ranking next to the author's.

## Where each number comes from

- 60 traces: `datasets/traces/traces.jsonl`.
- The author's ranking and saturation: `datasets/traces/author_taxonomy.json`. These are the author's draft numbers and can change; the tool reads the file each time.
- Saturation position: counted in the order you listed the traces, the first position at which each of your failure modes appears; the largest of those positions.
- `results.md` here is a stand-in learner's file produced by `tools/make_results.py`; it follows the author's draft taxonomy.

## Tests

`pytest challenges/challenge-2-error-analysis/part-2-taxonomy-and-criteria -q`. `test_rank_modes_uses_weights` needs weights of 1 to 3 and a ranking equal to count x weight. `test_saturation_marked` needs your `saturation_at` to equal the position the reading order gives. `test_taxonomy_and_criteria_pass_checks` runs both checklists.
