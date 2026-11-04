"""Shipped near-duplicate grouping (3.7): the learner reads it and calls it, never edits it."""
from __future__ import annotations

import re

WORD = re.compile(r"\w+")


def word_set(text: str) -> frozenset:
    """The lowercase words of a text, as a set."""
    return frozenset(WORD.findall(text.lower()))


def jaccard(a: frozenset, b: frozenset) -> float:
    """Shared words divided by all words of both: 1.0 for the same words, 0.0 for none in common."""
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def group_near_duplicates(cases: list, threshold: float = 0.8) -> list:
    """Group cases whose Jaccard overlap (lowercase word sets of `text`) is at least `threshold`.

    Overlap links cases, and linked cases share a group (A close to B and B close to C puts all three together).
    Returns a list of groups, each a list of cases sorted by id; groups are sorted by their first id.
    A case with no near twin is a group of one."""
    sets = [word_set(c["text"]) for c in cases]
    parent = list(range(len(cases)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            if jaccard(sets[i], sets[j]) >= threshold:
                parent[find(j)] = find(i)
    groups: dict = {}
    for i, c in enumerate(cases):
        groups.setdefault(find(i), []).append(c)
    out = [sorted(g, key=lambda c: c["id"]) for g in groups.values()]
    return sorted(out, key=lambda g: g[0]["id"])


def pairs_at_threshold(cases: list, threshold: float = 0.8) -> list:
    """Every pair (id, id, overlap) at or above the threshold, for printing."""
    sets = [word_set(c["text"]) for c in cases]
    out = []
    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            o = jaccard(sets[i], sets[j])
            if o >= threshold:
                out.append((cases[i]["id"], cases[j]["id"], round(o, 2)))
    return out
