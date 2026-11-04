"""Challenge 3, part 1: build your dataset v1 from the pool of 400 recorded tickets.

Shipped and read, not written:
  scrub_text(text)                          replaces emails and phone numbers (evalkit/scrub.py)
  group_near_duplicates(cases, threshold)   groups cases whose lowercase word sets overlap (evalkit/neardup.py)

Fill the five YOUR TURN gaps:
  1. select_cases(pool, dimensions, per_mix)      up to per_mix tickets for every combination of the dimensions
  2. drop_near_duplicates(cases, threshold)       one case per near-duplicate group
  3. tag_slices(cases, slice_rules)               add a "slices" list to every case
  4. split_cases(groups, heldout_share, seed)     dev and held-out, a group never split
  5. freeze(cases, name)                          sorted JSONL and its SHA-256

Your choices (dimensions, how many per mix, slices) are in my_dimensions.toml. Run the steps one by one:
    python -m evalkit dataset select --dims challenges/challenge-3-dataset/part-1-dataset-v1/my_dimensions.toml
    python -m evalkit dataset scrub
    python -m evalkit dataset dedupe
    python -m evalkit dataset split
    python -m evalkit dataset freeze --name v1
    python -m evalkit dataset compare
or all at once:  python challenges/challenge-3-dataset/part-1-dataset-v1/build_dataset.py
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit.neardup import group_near_duplicates  # noqa: E402,F401  (shipped, you call it)
from evalkit.scrub import scrub_text  # noqa: E402,F401  (shipped, you call it)


def select_cases(pool, dimensions, per_mix):
    """Pick up to `per_mix` pool tickets for every combination of the `dimensions` (a list of field names such as
    ["category", "tone"]). A combination with fewer tickets than per_mix gives all it has: never invent a case.
    Deterministic: inside a combination take tickets in id order. Return the chosen rows sorted by id."""
    raise NotImplementedError("YOUR TURN: group the pool by the tuple of dimension values, keep the first per_mix of each group by id, sort by id")


def drop_near_duplicates(cases, threshold):
    """Keep one case from every near-duplicate group (the one with the lowest id). Return the kept cases sorted by id.
    Call the shipped group_near_duplicates(cases, threshold)."""
    raise NotImplementedError("YOUR TURN: groups = group_near_duplicates(cases, threshold); keep the first case of each group; sort by id")


def tag_slices(cases, slice_rules):
    """`slice_rules` maps a slice name to the field values that put a case in it, for example
    {"delivery": {"category": "delivery"}, "angry_or_confused": {"tone": ["angry", "confused"]}}.
    A value may be one value or a list of allowed values; a case is in the slice when every field matches.
    Return copies of the cases, each with a "slices" list of the names it belongs to (sorted; empty when none)."""
    raise NotImplementedError("YOUR TURN: for each case compute the matching rule names and store them under 'slices'")


def split_cases(groups, heldout_share, seed):
    """`groups` is the output of group_near_duplicates: a list of lists of cases. Put whole groups into "dev" or
    "heldout" so that a near-duplicate group is never split. About heldout_share of the cases go to held-out.
    Deterministic for a seed (use random.Random(seed)). Return copies of all cases with a "split" field."""
    raise NotImplementedError("YOUR TURN: shuffle the groups with random.Random(seed); fill held-out until it holds about heldout_share of the cases")


def freeze(cases, name):
    """Make the frozen file. Sort the cases by id, write each as one JSON line (keys sorted, no ASCII escaping, a
    newline after every line), and hash the whole text with SHA-256.
    Return {"name": name, "n": number of cases, "body": the text, "hash": the 64-character hex hash}."""
    raise NotImplementedError("YOUR TURN: sort by id, json.dumps(sort_keys=True, ensure_ascii=False) per line, sha256 of the utf-8 body")


def main():
    """The whole pipeline in memory, from my_dimensions.toml. The CLI commands do the same steps one at a time."""
    from evalkit import dataset_cli

    dataset_cli.run_all(Path(__file__).with_name("my_dimensions.toml"), Path(__file__))


if __name__ == "__main__":
    main()
