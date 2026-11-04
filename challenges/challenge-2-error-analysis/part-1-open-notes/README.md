# Challenge 2, part 1: write open notes on 30 traces

Time: 60 minutes. Nothing here calls a model: the traces are files. No AI assistant writes your notes; the point is that you read.

## Words you need

- **Trace**: one recorded run of the reply feature: the customer's ticket and the reply the assistant wrote. `datasets/traces/traces.jsonl` holds 60. You read `tr01` to `tr30`; the other 30 carry the author's notes and you open them in part 2.
- **Open note**: one sentence you write about one trace, before you have any categories. It says what the reply did or claimed that it should not have, or "No failure found" and why.
- **Failure**: something in the reply that a careful support lead would not send: a fact it cannot know, an action it cannot take, a promise the policy does not give.
- **Flagged note**: the tool refuses the note because it is under 8 words, or because it names no failure.

## The idea from zero

Nobody can grade what nobody has named. Before you write any grader, you read real outputs and say, in your own words, what went wrong. The notes are the raw material: in part 2 you group them into counted modes and write three criteria from the biggest ones.

A note like "bad reply" tells you nothing a month later. A note like "Says the customer is inside the 7 day window with no delivery date given" tells you what to measure.

## Steps

1. `python -m evalkit notes`. It shows trace 1 of your 30 and starts a timer. Read the ticket and the reply, type one note, press Enter.
2. If the tool flags the note ("under 8 words", "names no failure"), fix it and press Enter again. The tool never saves a flagged note.
3. Go on to trace 30. The tool saves `my_notes.jsonl` after every note (trace id, note, seconds), so you can stop and run `notes` again to continue.
4. When you finish it prints your median time per trace. If the median is under 25 seconds it warns you and names the three fastest traces: reread them and rewrite the notes.
5. `python -m evalkit notes --check` until it says 30 clean, 0 flagged, 0 missing.
6. `python challenges/challenge-2-error-analysis/part-1-open-notes/notes_summary.py` prints the words you reused most. Write them in `results.md`: they become your mode names in part 2.
7. Fill in `results.md`.

You write no code in this part. Your work is `my_notes.jsonl` and `results.md`.

## Where each number comes from

- 30 traces: `tr01` to `tr30` of `datasets/traces/traces.jsonl` (the file holds 60).
- 8 words and 25 seconds: the rules chapter 2.2 set. Eight words is room for what happened and where; under 25 seconds a trace is skimmed, not read.
- Seconds per note: from the tool's timer, from showing the trace to accepting the note (flagged tries are included).
- `results.md` in this folder is a stand-in learner's file (the author's own notes and timings), produced by `tools/make_results.py` from `my_notes.jsonl`.

## Tests

`pytest challenges/challenge-2-error-analysis/part-1-open-notes -q`. `test_thirty_clean_notes` is the one that fails until your file holds 30 clean notes in your own words. The other tests check the two rules of the tool.
