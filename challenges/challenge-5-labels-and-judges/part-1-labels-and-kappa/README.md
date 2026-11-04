# Challenge 5, part 1: label 30 replies and check yourself against the expert

Time: 60 minutes. Replay only: the replies are files, nothing calls a model, no key. "Before you grade a judge, find out how well you grade."

## Words you need

- **Criterion**: the question every reply is graded against. Here: does the reply state FreshMarket's refund policy correctly? It applies to replies to refund tickets only.
- **Label**: your verdict on one reply, `pass` or `fail`. Fail is the positive class in this whole module.
- **Expert label**: the author's verdict, with a reason. In this repository the expert labels are drafts (a model's first pass that the author reads and accepts or changes) until `datasets/labels/expert_labels.jsonl` exists; every results file says which one it used.
- **Calibration set**: 10 replies. After each label you see the expert's label and reason. It teaches you the guideline and is not scored.
- **Blind set**: 20 replies. No reasons. Scored once.
- **Agreement**: the share of replies where you and the expert give the same label.
- **Cohen's kappa**: agreement corrected for the agreement you would get by chance. 1 is perfect, 0 is no better than chance.

## The idea from zero

Two people label the same 20 replies. Suppose 18 labels agree: 90%. That sounds good, but if almost every reply is a pass, two people who always say "pass" agree 90% of the time without reading anything. Kappa subtracts that. With the real table the cells are: both pass, you pass and the expert fails, you fail and the expert passes, both fail. Chance agreement `pe` adds, for each label, your share of that label times the expert's share. Then `kappa = (po - pe) / (1 - pe)` where `po` is the agreement you saw. If `pe` is 1 (every label the same on both sides) kappa is undefined and the function returns `None`.

Two worked tables to check yourself against: cells 88, 5, 5, 2 give kappa 0.232 although agreement is 90%; cells 45, 5, 5, 45 give 0.80 with the same 90%.

## Steps (the file is [kappa.py](kappa.py))

1. Why (5 min): read the safety line above and the glossary.
2. Calibration (12 min): `python -m evalkit label --calibration`. Label each of the 10 replies, read the expert's reason after it. At least 3 of the 10 are expert fails.
3. Blind labels (18 min): `python -m evalkit label --blind`. 20 replies, at least 6 expert fails, no reasons. Your labels are saved in `my_labels_blind.jsonl`.
4. Write `cohen_kappa(mine, expert)` and `needs_reread(kappa)` in `kappa.py` and run the tests (12 min).
5. Run `python -m evalkit kappa`: it prints the four cells, agreement and kappa (5 min). Kappa on 20 labels is noisy: one reply moves it by several points. Read the cells, not kappa alone.
6. For each disagreement write a reconciliation note: `python -m evalkit label --note ID "your note"` (8 min). The label file is never rewritten; the note goes to `reconcile.jsonl`.
7. In `results.md` say why 30 labels is a practice size and not a production one (S3 gives 100 to 200 labels per failure mode as one team's guidance) (5 min).

`label --calibration --from FILE` and `label --blind --from FILE` read the labels from a file instead of asking; the reference `results.md` was made that way from a stand-in learner (`tools/standin_labels.py`).

## Where each number comes from

- The 30 replies: `datasets/labels/label_set.jsonl` (splits `calibration` and `blind`). The expert's labels and reasons: the drafts in the same file, or `expert_labels.jsonl` when the author has confirmed them.
- The cells and kappa: your `kappa.py` on your `my_labels_blind.jsonl` against the expert's blind labels. The learner's labels are never used later; dev and test use the expert's. The comparison with the expert is the lesson.
- `results.md` here is a stand-in learner's file made by `tools/make_results.py`.

## Tests

`pytest challenges/challenge-5-labels-and-judges/part-1-labels-and-kappa -q`. `test_known_table`, `test_undefined_when_pe_is_one` and `test_reconcile_never_overwrites` fail until `cohen_kappa` is written. `test_checkpoint_1` needs your calibration labels and the line "Matched the expert on N of 10"; `test_checkpoint_2` needs the cells, kappa and a note for every disagreement in `results.md`.
