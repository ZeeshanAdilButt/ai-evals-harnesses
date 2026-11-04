# Challenge 3, part 1: build your dataset v1

Time: 80 minutes, in three checkpoints. Replay only: nothing here calls a model. Every ticket in the pool (`datasets/pool/tickets.jsonl`, 400 tickets) is already recorded for variants A and B, five trials each, and every recording was made on the ticket's scrubbed `text`. So whatever you choose, replay never misses.

## Words you need

- **Pool**: the 400 recorded candidate tickets. Each has dimensions: `category` (billing, delivery, refund, account, product), `urgent`, `tone` (calm, angry, confused), `language` (english, mixed), `length` (short, normal, long), `source` (synthetic, sampled, past_failure, edge) and `easy`.
- **Mix**: one combination of dimension values, for example refund + angry + mixed. A good dataset covers the mixes production has, not only the easy ones.
- **Scrub**: replace emails and phone numbers before a ticket is stored. The shipped `scrub_text` does it with two patterns; `raw_text` holds the original, `text` the scrubbed one.
- **Near duplicate**: two tickets whose lowercase word sets overlap by at least 0.8 (Jaccard: shared words divided by all words). Keeping both inflates the score and, if one lands in held-out, leaks the other.
- **Slice**: a named part of the data you report on separately ("delivery", "angry"). A slice with fewer than 10 cases is thin.
- **Split**: dev (you tune on it) and held-out (you look once). A near-duplicate group must stay in one split.
- **Freeze and hash**: write the cases sorted by id, once, and record a SHA-256 of the file. The same bytes give the same hash; any change gives a new one. A hash says nothing about whether the cases are good.

## The idea from zero

Your graders are only as honest as your cases. You build your own dataset v1 from the pool and compare it with canonical v1. Modules 4 to 9 always run canonical v1, so an unfinished or unusual v1 never breaks a later chapter.

## Steps (the file is [build_dataset.py](build_dataset.py); your choices are in [my_dimensions.toml](my_dimensions.toml))

**Checkpoint 1: dimensions, select, scrub (about 30 min).**
1. Read `build_dataset.py` and the shipped `scrub_text` ([evalkit/scrub.py](../../../evalkit/scrub.py)): two patterns, one for emails and one for phone numbers (8 min).
2. Pick your `dimensions`, `per_mix` and slices in `my_dimensions.toml` from your taxonomy and chapter 3.3, and write one line for each dimension saying why (8 min).
3. Write `select_cases` (line 37), then `python -m evalkit dataset select --dims challenges/challenge-3-dataset/part-1-dataset-v1/my_dimensions.toml`. If a mix has too few tickets the tool says which and suggests another filter; it never records new cases.
4. `python -m evalkit dataset scrub`. It scrubs each selected `raw_text` and checks that the result equals the pool's `text` (14 min for steps 3 and 4).

**Checkpoint 2: dedupe, slices, split (about 30 min).**
5. Write `drop_near_duplicates` (8 min) and `tag_slices` (8 min), then `split_cases` (10 min).
6. `python -m evalkit dataset dedupe` prints the pairs it drops; `python -m evalkit dataset split` prints the counts and the slice table (4 min).

**Checkpoint 3: freeze, compare, differences (about 20 min).**
7. Write `freeze`, then `python -m evalkit dataset freeze --name v1` and read the per-slice table with n for each slice (6 min).
8. `python -m evalkit dataset compare` lists the differences from canonical v1. Write one line for each: cases only in yours, only in canonical, slices missing or thin (8 min).
9. Write the interview answer ("How did you make sure your eval set looks like production?") and score it (6 min).

The whole pipeline in one go: `python challenges/challenge-3-dataset/part-1-dataset-v1/build_dataset.py`.

## Where each number comes from

- 400 tickets and their dimensions: `datasets/pool/tickets.jsonl`.
- The near-duplicate threshold 0.8: `dedupe_threshold` in your file; the Jaccard overlap is computed by [evalkit/neardup.py](../../../evalkit/neardup.py). Three pool pairs reach 0.8; canonical v1 contains none.
- Held-out share: `heldout_share` of the cases after dedupe, whole groups at a time, shuffled with your `seed`.
- Canonical v1 (160 cases, 120 dev and 40 held-out, hash `8c7f508c426d...`): `datasets/canonical/v1/`. Your files are in `datasets/mine/`.
- `results.md` in this folder is a stand-in learner's file produced by `tools/make_results.py`.

## Tests

`pytest challenges/challenge-3-dataset -q`. `test_scrub_matches_text` passes from the start. `test_checkpoint_1` runs `test_select_respects_dimensions` and checks your dimensions section; `test_checkpoint_2` runs the dedupe, tag and split tests and checks your counts; `test_checkpoint_3` runs `test_freeze_hash_is_order_independent` and checks your hash, your differences and your answer. If you stop, resume at the first checkpoint whose test fails.
