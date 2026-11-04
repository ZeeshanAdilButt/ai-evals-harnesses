"""Challenge 3, part 1. test_checkpoint_1 to test_checkpoint_3 are the three checkpoints of results.md.
The five gap tests fail on the starter with NotImplementedError; test_scrub_matches_text passes there (the scrubber is shipped).
If you stop, start again at the first checkpoint whose test fails."""
import hashlib
import importlib.util
import json
import random
import re
from pathlib import Path

from evalkit import dataset_cli
from evalkit.neardup import group_near_duplicates, jaccard, word_set
from evalkit.scrub import scrub_text

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def learner():
    spec = importlib.util.spec_from_file_location("learner_build_dataset_test", HERE / "build_dataset.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pool():
    return dataset_cli.read_jsonl(ROOT / "datasets/pool/tickets.jsonl")


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def pipeline():
    """Your five functions run on your dimensions file, in memory."""
    mod = learner()
    cfg = dataset_cli.load_dims(HERE / "my_dimensions.toml")
    chosen = mod.select_cases(dataset_cli.apply_filters(pool(), cfg["filters"]), cfg["dimensions"], cfg["per_mix"])
    scrubbed = [{k: v for k, v in r.items() if k != "raw_text"} | {"text": scrub_text(r["raw_text"])} for r in chosen]
    kept = mod.drop_near_duplicates(scrubbed, cfg["dedupe_threshold"])
    tagged = mod.tag_slices(kept, cfg["slices"])
    split = mod.split_cases(group_near_duplicates(tagged, cfg["dedupe_threshold"]), cfg["heldout_share"], cfg["seed"])
    frozen = mod.freeze([dataset_cli.to_case(r) for r in split], "v1")
    return cfg, chosen, kept, split, frozen


def tiny_pool():
    rows = []
    n = 0
    for cat in ("billing", "refund"):
        for tone in ("calm", "angry"):
            for k in range(3 if (cat, tone) != ("refund", "angry") else 1):
                n += 1
                rows.append({"id": f"p{n:02d}", "category": cat, "tone": tone, "text": f"{cat} {tone} ticket number {k} about order {n}"})
    return rows


def test_scrub_matches_text():
    """The shipped scrubber turns every pool raw_text into the pool's text, so every recording still hits."""
    rows = pool()
    bad = [r["id"] for r in rows if scrub_text(r["raw_text"]) != r["text"]]
    assert not bad, f"scrub_text differs from text for {bad[:5]}"
    assert any(r["raw_text"] != r["text"] for r in rows)


def test_select_respects_dimensions():
    mod = learner()
    rows = tiny_pool()
    chosen = mod.select_cases(rows, ["category", "tone"], 2)
    by_mix = {}
    for r in chosen:
        by_mix.setdefault((r["category"], r["tone"]), []).append(r["id"])
    assert set(by_mix) == {("billing", "calm"), ("billing", "angry"), ("refund", "calm"), ("refund", "angry")}, "one group for every mix"
    assert {k: len(v) for k, v in by_mix.items()} == {("billing", "calm"): 2, ("billing", "angry"): 2, ("refund", "calm"): 2, ("refund", "angry"): 1}, (
        "per_mix tickets for a mix that has them, all it has for a thin mix, never more")
    assert [r["id"] for r in chosen] == sorted(r["id"] for r in chosen), "sorted by id"
    assert mod.select_cases(rows, ["category", "tone"], 2) == chosen, "same input, same output"
    # the real pool
    cfg = dataset_cli.load_dims(HERE / "my_dimensions.toml")
    real = dataset_cli.apply_filters(pool(), cfg["filters"])
    got = mod.select_cases(real, cfg["dimensions"], cfg["per_mix"])
    avail, taken = {}, {}
    for r in real:
        avail[tuple(r[d] for d in cfg["dimensions"])] = avail.get(tuple(r[d] for d in cfg["dimensions"]), 0) + 1
    for r in got:
        taken[tuple(r[d] for d in cfg["dimensions"])] = taken.get(tuple(r[d] for d in cfg["dimensions"]), 0) + 1
    assert {k: min(n, cfg["per_mix"]) for k, n in avail.items()} == taken
    assert {r["id"] for r in got} <= {r["id"] for r in real}, "only pool tickets: the tool never invents a case"


def test_dedupe_drops_near_duplicates():
    mod = learner()
    cases = [
        {"id": "a1", "text": "Can I move my Friday delivery slot to Saturday morning?"},
        {"id": "a2", "text": "Can I move my Friday slot to Saturday morning?"},
        {"id": "b1", "text": "The bananas in order 12 were rotten."},
        {"id": "c1", "text": "How do I delete my account?"},
        {"id": "c2", "text": "how do i delete my account? thanks"},
        {"id": "d1", "text": "Please refund the missing bananas from order FM-640321."},
    ]
    assert jaccard(word_set(cases[0]["text"]), word_set(cases[1]["text"])) >= 0.8
    kept = mod.drop_near_duplicates(cases, 0.8)
    assert [c["id"] for c in kept] == ["a1", "b1", "c1", "d1"], "one case per group, the lowest id"
    assert len(mod.drop_near_duplicates(cases, 0.99)) == 6, "a stricter threshold keeps more"
    real = pool()
    kept_real = mod.drop_near_duplicates(real, 0.8)
    assert len(kept_real) == len(group_near_duplicates(real, 0.8))


def test_tag_slices_adds_every_rule():
    mod = learner()
    cases = [{"id": "x1", "category": "delivery", "tone": "angry"}, {"id": "x2", "category": "billing", "tone": "angry"},
             {"id": "x3", "category": "delivery", "tone": "calm"}, {"id": "x4", "category": "account", "tone": "calm"}]
    rules = {"delivery": {"category": "delivery"}, "angry": {"tone": ["angry", "confused"]}, "angry_delivery": {"category": "delivery", "tone": "angry"}}
    out = {c["id"]: c["slices"] for c in mod.tag_slices(cases, rules)}
    assert out == {"x1": ["angry", "angry_delivery", "delivery"], "x2": ["angry"], "x3": ["delivery"], "x4": []}
    assert "slices" not in cases[0], "do not change the input cases"


def test_split_has_no_cross_split_duplicates():
    mod = learner()
    cases = [{"id": f"s{i:02d}", "text": f"unique ticket about thing {i} and also item number {i * 7}"} for i in range(40)]
    cases.append({"id": "s40", "text": cases[3]["text"] + " please"})
    groups = group_near_duplicates(cases, 0.8)
    out = mod.split_cases(groups, 0.25, 7)
    side = {c["id"]: c["split"] for c in out}
    assert len(out) == 41 and set(side.values()) == {"dev", "heldout"}
    for g in groups:
        assert len({side[c["id"]] for c in g}) == 1, f"group {[c['id'] for c in g]} is split"
    assert abs(sum(1 for v in side.values() if v == "heldout") - 41 * 0.25) <= 2
    assert mod.split_cases(groups, 0.25, 7) == out, "same seed, same split"
    assert mod.split_cases(groups, 0.25, 8) != out, "another seed, another split"
    # your own data: no pair above the threshold crosses the split
    cfg, _, _, split, _ = pipeline()
    dev = [c for c in split if c["split"] == "dev"]
    held = [c for c in split if c["split"] == "heldout"]
    ws = {c["id"]: word_set(c["text"]) for c in split}
    assert not [(a["id"], b["id"]) for a in dev for b in held if jaccard(ws[a["id"]], ws[b["id"]]) >= cfg["dedupe_threshold"]]


def test_freeze_hash_is_order_independent():
    mod = learner()
    cases = [{"id": f"c{i}", "text": f"text {i}", "expected": {"category": "billing", "urgent": False}} for i in (3, 1, 2)]
    a = mod.freeze(cases, "v1")
    b = mod.freeze(list(reversed(cases)), "v1")
    assert a["hash"] == b["hash"] and a["body"] == b["body"], "freeze sorts first, so the order you list cases does not matter"
    assert a["hash"] == hashlib.sha256(a["body"].encode("utf-8")).hexdigest() and len(a["hash"]) == 64
    assert [json.loads(l)["id"] for l in a["body"].splitlines()] == ["c1", "c2", "c3"] and a["body"].endswith("\n") and a["n"] == 3
    changed = [dict(c) for c in cases]
    changed[0]["text"] = "text 3 "
    assert mod.freeze(changed, "v1")["hash"] != a["hash"], "one changed character, a new hash"
    # the same recipe reproduces canonical dataset v1 exactly
    canon = dataset_cli.read_jsonl(ROOT / "datasets/canonical/v1/cases.jsonl")
    shuffled = canon[:]
    random.Random(1).shuffle(shuffled)
    assert mod.freeze(shuffled, "v1")["hash"] == (ROOT / "datasets/canonical/v1/HASH").read_text(encoding="utf-8").strip()


def lines(body, label):
    m = re.search(rf"^{label}: (.+)$", body, flags=re.M)
    assert m, f"write a line '{label}: ...'"
    return m.group(1).strip()


def test_checkpoint_1():
    test_select_respects_dimensions()
    body = section("Checkpoint 1")
    cfg, chosen, _, _, _ = pipeline()
    dims = [d.strip() for d in lines(body, "Dimensions").split(",")]
    assert dims == cfg["dimensions"], "the Dimensions line must list the dimensions in my_dimensions.toml"
    why = re.findall(r"^Why (\w+): (.+)$", body, flags=re.M)
    assert {w for w, _ in why} >= set(dims) and all(PLACEHOLDER not in t and len(t.split()) >= 4 for _, t in why), "say why for each dimension, in a line"
    assert lines(body, "Selected") == str(len(chosen))
    assert "scrub" in body.lower() and PLACEHOLDER not in body


def test_checkpoint_2():
    test_dedupe_drops_near_duplicates()
    test_tag_slices_adds_every_rule()
    test_split_has_no_cross_split_duplicates()
    body = section("Checkpoint 2")
    _, _, kept, split, _ = pipeline()
    assert lines(body, "After dedupe") == str(len(kept))
    assert lines(body, "Dev") == str(sum(1 for c in split if c["split"] == "dev"))
    assert lines(body, "Held-out") == str(sum(1 for c in split if c["split"] == "heldout"))
    assert PLACEHOLDER not in body


def test_checkpoint_3():
    test_freeze_hash_is_order_independent()
    body = section("Checkpoint 3")
    _, _, _, _, frozen = pipeline()
    assert lines(body, "Hash") == frozen["hash"], "write the hash that `dataset freeze` printed"
    diff = body.split("### Differences", 1)[-1].split("### Interview answer", 1)[0] if "### Differences" in body else ""
    assert len([l for l in diff.splitlines() if l.strip().startswith("- ")]) >= 3 and PLACEHOLDER not in diff, (
        "under '### Differences from canonical v1' write one line (starting with '- ') for each difference")
    answer = body.split("### Interview answer", 1)[-1] if "### Interview answer" in body else ""
    assert len(answer.strip()) > 80 and PLACEHOLDER not in answer, "write your interview answer under '### Interview answer'"
