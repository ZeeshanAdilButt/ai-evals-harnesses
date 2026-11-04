"""Tag the must-pass cases of canonical datasets v1 and v2 (the author's tag, read by the ship gate in 9.7).

A canonical case is must-pass for the reply feature when it is a refund-window refund ticket (tools/make_reply_checks.py sets
refund_days for it) AND the baseline, variant A, passes every reply check on all five recorded trials. The second condition is
what makes the rule fair: the gate blocks any must-pass case under 5 of 5 trials, so a case that the shipped baseline itself
fails must not carry the tag. The refund-window tickets that A does not pass five times stay untagged and are listed.

Run after tools/make_reply_checks.py; it rewrites cases.jsonl and HASH of v1 and v2 (the hash changes when a tag changes):
    .venv/Scripts/python.exe tools/tag_must_pass.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.graders import reply as reply_graders  # noqa: E402
from evalkit.replay import Store  # noqa: E402
from product import reply  # noqa: E402


def read(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def write(folder: Path, cases: list):
    body = "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in cases)
    (folder / "cases.jsonl").write_bytes(body.encode("utf-8"))
    (folder / "HASH").write_bytes((hashlib.sha256(body.encode("utf-8")).hexdigest() + "\n").encode("utf-8"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def main():
    store = Store.load("reply")
    checks = reply_graders.all_checks()
    v1 = read(ROOT / "datasets/canonical/v1/cases.jsonl")
    tagged, window_untagged = set(), []
    for c in v1:
        ck = checks[c["id"]]
        if ck["refund_days"] is None:
            continue
        key = reply.build_request("A", c["text"])["key"]
        if all(reply_graders.grade_reply_facts(store.lookup(key, t)["output"], ck) for t in range(1, 6)):
            tagged.add(c["id"])
        else:
            window_untagged.append(c["id"])
    for c in v1:
        c["must_pass"] = c["id"] in tagged
    h1 = write(ROOT / "datasets/canonical/v1", v1)
    v2 = read(ROOT / "datasets/canonical/v2/cases.jsonl")
    for c in v2:
        c["must_pass"] = c["id"] in tagged
    h2 = write(ROOT / "datasets/canonical/v2", v2)
    print(f"must-pass reply cases: {len(tagged)}: {', '.join(sorted(tagged))}")
    print(f"refund-window tickets that A does not pass on all five trials (left untagged): {len(window_untagged)}")
    print(f"canonical v1 hash {h1}\ncanonical v2 hash {h2}")


if __name__ == "__main__":
    main()
