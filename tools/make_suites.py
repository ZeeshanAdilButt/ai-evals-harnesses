"""Write suites/*.toml. The m1-triage case list is chosen from the recordings (replay only):
ten canonical v1 dev cases where A and B pass the same number of trial-1 cases and at least one case
flips each way. Run once; the output is committed.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.graders.shipped import match, schema  # noqa: E402
from evalkit.replay import Store  # noqa: E402
from product import triage  # noqa: E402

cases = [json.loads(l) for l in (ROOT / "datasets/canonical/v1/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
store = Store.load("triage")


def passed(variant, c):
    out = store.lookup(triage.build_request(variant, c["text"])["key"], 1)["output"]
    return schema(out, c) and match(out, c)


dev = sorted((c for c in cases if c["split"] == "dev"), key=lambda c: c["id"])
kind = {c["id"]: (passed("A", c), passed("B", c)) for c in dev}
want = {"to_pass": (False, True), "to_fail": (True, False), "both_fail": (False, False), "both_pass": (True, True)}
take = {"to_pass": 2, "to_fail": 2, "both_fail": 1, "both_pass": 5}
chosen, cats_used = [], {}
for name, n in take.items():
    pool = [c for c in dev if kind[c["id"]] == want[name]]
    pool.sort(key=lambda c: (cats_used.get(c["expected"]["category"], 0), c["id"]))
    for c in pool:
        if sum(1 for x in chosen if x[1] == name) >= n:
            break
        chosen.append((c["id"], name))
        cats_used[c["expected"]["category"]] = cats_used.get(c["expected"]["category"], 0) + 1
ids = "t001 t008 t017 t071 t002 t074 t312 t207 t006 t330".split()  # fixed by the coordinator (chapter 1.3 shows them)
kind = {c["id"]: (passed("A", c), passed("B", c)) for c in cases}
a = sum(kind[i][0] for i in ids)
b = sum(kind[i][1] for i in ids)
assert len(ids) == 10 and a == b == 6, (ids, a, b)
print("m1 ids", ids, "pass A", a, "pass B", b)

V1 = "datasets/canonical/v1/cases.jsonl"
TRI = ["schema", "match"]
REP = ["reply_nonempty"]


def toml_list(xs):
    return "[" + ", ".join(json.dumps(x) for x in xs) + "]"


def part(feature, dataset, trials, graders, ids=None, split=None):
    s = f'\n[[part]]\nfeature = "{feature}"\ndataset = "{dataset}"\ntrials = {trials}\n'
    if ids:
        s += f"cases = {toml_list(ids)}\n"
    if split:
        s += f'split = "{split}"\n'
    return s + f"graders = {toml_list(graders)}\n"


def suite(name, desc, parts):
    return f'name = "{name}"\ndescription = "{desc}"\n' + "".join(parts)


# smoke: a subset of full. The learner builds the real one in 9.7 from the must_pass tags; this
# reference version takes the first four dev cases of each category until those tags exist.
smoke_ids = []
for cat in ["billing", "delivery", "refund", "account", "product"]:
    smoke_ids += [c["id"] for c in dev if c["expected"]["category"] == cat][:4]
smoke_ids = sorted(set(smoke_ids) | set(c["id"] for c in cases if c.get("must_pass")))

suites = {
    "m1-triage": suite("m1-triage", "Module 1: ten canonical v1 cases, triage, trial 1 only. A and B pass the same number, and cases flip both ways.",
                       [part("triage", V1, 1, TRI, ids=ids)]),
    "v1-triage": suite("v1-triage", "Canonical dataset v1 (160 cases), triage, trial 1.", [part("triage", V1, 1, TRI)]),
    "v1-reply": suite("v1-reply", "Canonical dataset v1 (160 cases), reply, trial 1. Reply graders arrive in module 4; this runs the placeholder.",
                      [part("reply", V1, 1, REP)]),
    "pool400": suite("pool400", "All 400 pool tickets, triage, trial 1. For the pool (6.6) and for retries and resume (6.8).",
                     [part("triage", "datasets/pool/tickets.jsonl", 1, TRI)]),
    "agent40": suite("agent40", "The 40 refund tasks, five trials, graded from the recorded tool loops by the state and trajectory graders.",
                     [part("agent", "datasets/agent_tasks.jsonl", 5, ["agent_state", "agent_trajectory"])]),
    "smoke": suite("smoke", "A subset of full, five trials. Reference version: four dev cases per category (the learner builds the real one in 9.7).",
                   [part("triage", V1, 5, TRI, ids=smoke_ids), part("reply", V1, 5, REP_FACTS, ids=smoke_ids)]),
    "full": suite("full", "Canonical v1 (triage and reply) and the 40 agent tasks, five trials.",
                  [part("triage", V1, 5, TRI), part("reply", V1, 5, REP),
                   part("agent", "datasets/agent_tasks.jsonl", 5, ["agent_state", "agent_trajectory"])]),
    "release": suite("release", "Canonical v2 (triage and reply) and the 40 agent tasks, five trials.",
                     [part("triage", "datasets/canonical/v2/cases.jsonl", 5, TRI), part("reply", "datasets/canonical/v2/cases.jsonl", 5, REP_FACTS),
                      part("agent", "datasets/agent_tasks.jsonl", 5, ["agent_state", "agent_trajectory"])]),
}
(ROOT / "suites").mkdir(exist_ok=True)
for n, body in suites.items():
    (ROOT / "suites" / f"{n}.toml").write_text(body, encoding="utf-8")
print("wrote", ", ".join(suites))
