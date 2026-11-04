"""Module 5 commands: label, kappa, judge-eval, choose, judge-probes (shipped, finished). Replay only: no command here calls a model.

The pieces the learner writes live in the challenge 5 scripts and are loaded here:
  part-1-labels-and-kappa/kappa.py          cohen_kappa, needs_reread
  part-2-judge-comparison/judge_rule.py     tpr_tnr, choose_judge
A gap that is not filled yet raises NotImplementedError("YOUR TURN: ..."); the commands print it and stop.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import sys
from pathlib import Path

from evalkit import labels, stats
from evalkit.replay import ReplayMiss, Store
from judges.parts import ALL_JUDGES
from product.judge import build_request, parse_verdict

ROOT = labels.ROOT
CH5 = ROOT / "challenges" / "challenge-5-labels-and-judges"
P1 = CH5 / "part-1-labels-and-kappa"
P2 = CH5 / "part-2-judge-comparison"
RUNS = ROOT / "runs"
DEV_DIR = RUNS / "judge-dev"
LOCK = RUNS / "judge-test.lock"
TPR_FLOOR = 0.85
PADDED_ITEMS = ROOT / "datasets" / "judge_items" / "padded.jsonl"
SECOND = ROOT / "recordings" / "judge" / "v3-second.jsonl"
HAS_EXAMPLES = lambda j: j not in ("v1", "v2")  # noqa: E731


class NotRecorded(Exception):
    pass


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canon(judge: str) -> str:
    """d1r1e1 is the same prompt as v3 and is an alias."""
    if judge == "d1r1e1":
        return "v3"
    if judge not in ALL_JUDGES:
        raise SystemExit(f"unknown judge {judge!r}: v1, v2, v3 or a builder id d{{0,1}}r{{0,1}}e{{1,2,3}} (d1r1e1 is v3)")
    return judge


# ---------------------------------------------------------------------------------------------------------------------------
# label and kappa

def _shown(row: dict) -> str:
    return f"Ticket: {row['ticket']}\n\nReply:\n{row['reply']}\n"


def cmd_label(argv: list[str]) -> int:
    """label --calibration | --blind [--from FILE] [--out FILE] | --note ID TEXT [--set blind]"""
    flags = set(argv)
    if "--note" in argv:
        i = argv.index("--note")
        add_note(P1 / "reconcile.jsonl", argv[i + 1], " ".join(argv[i + 2:]))
        print(f"note saved for {argv[i + 1]} in {(P1 / 'reconcile.jsonl').relative_to(ROOT).as_posix()}; your label was not changed")
        return 0
    which = "calibration" if "--calibration" in flags else "blind" if "--blind" in flags else None
    if not which:
        print("usage: label --calibration | label --blind [--from FILE] [--out FILE] | label --note ID TEXT")
        return 2
    items = labels.split_items(which)
    verdicts, reasons, source = labels.expert_labels()
    fails = sum(verdicts[r["id"]] == "fail" for r in items)
    need = 3 if which == "calibration" else 6
    if fails < need:
        print(f"the {which} set has {fails} expert fails; it needs at least {need} so that kappa is defined. Tell the author.")
        return 1
    opt = lambda f, d=None: argv[argv.index(f) + 1] if f in argv else d  # noqa: E731
    out = Path(opt("--out", P1 / f"my_labels_{which}.jsonl"))
    src = opt("--from")
    given = {r["id"]: r["label"] for r in labels.read_jsonl(src)} if src else {}
    print(f"{which}: {len(items)} replies. Label each one pass or fail against the criterion: does the reply state the refund policy correctly?")
    if which == "calibration":
        print("After each label you see the expert's label and reason. This set is for learning the guideline; it is not scored.")
    else:
        print("No reasons are shown. This set is scored once, by `kappa`.")
    mine = []
    for n, row in enumerate(items, 1):
        if src:
            answer = given[row["id"]]
        else:
            print(f"\n[{n}/{len(items)}] {row['id']}\n{_shown(row)}")
            answer = ""
            while answer not in ("pass", "fail"):
                answer = input("your label (pass or fail): ").strip().lower()
        mine.append({"id": row["id"], "label": answer})
        if which == "calibration":
            same = "agree" if answer == verdicts[row["id"]] else "DISAGREE"
            print(f"[{n}/{len(items)}] {row['id']}: you {answer}, expert {verdicts[row['id']]} ({same}). Expert reason: {reasons[row['id']]}")
        elif src:
            print(f"[{n}/{len(items)}] {row['id']}: you {answer}")
    if not src:
        out.write_text("".join(json.dumps(m) + "\n" for m in mine), encoding="utf-8")
        print(f"\nsaved {len(mine)} labels to {out}")
    else:
        print(f"read {len(mine)} labels from {src}")
    return 0


def add_note(path: Path, item_id: str, text: str) -> None:
    """Append a reconciliation note. The label files are never opened for writing, so a label is never overwritten."""
    with Path(path).open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"id": item_id, "note": text}, ensure_ascii=False) + "\n")


def cmd_kappa(argv: list[str]) -> int:
    opt = lambda f, d=None: argv[argv.index(f) + 1] if f in argv else d  # noqa: E731
    which = opt("--expert", "blind")
    mine_path = Path(opt("--mine", P1 / f"my_labels_{which}.jsonl"))
    items = labels.split_items(which)
    verdicts, _, source = labels.expert_labels()
    if not mine_path.exists():
        print(f"no labels at {mine_path}: run `python -m evalkit label --{which}` first")
        return 1
    mine = {r["id"]: r["label"] for r in labels.read_jsonl(mine_path)}
    if set(mine) != {r["id"] for r in items}:
        print(f"{mine_path.name} must hold exactly the {len(items)} {which} replies")
        return 1
    ids = [r["id"] for r in items]
    m, e = [mine[i] for i in ids], [verdicts[i] for i in ids]
    mod = load_module(P1 / "kappa.py", "learner_kappa")
    cells = mod.agreement_cells(m, e)
    agree = (cells["both_pass"] + cells["both_fail"]) / len(ids)
    print(f"{which} set: {len(ids)} replies, {sum(x == 'fail' for x in e)} expert fails. {labels.source_line()}")
    print(f"cells (yours / expert): both pass {cells['both_pass']}, you pass and expert fail {cells['mine_pass_expert_fail']}, "
          f"you fail and expert pass {cells['mine_fail_expert_pass']}, both fail {cells['both_fail']}")
    print(f"agreement {100 * agree:.1f}%")
    try:
        k = mod.cohen_kappa(m, e)
        reread = mod.needs_reread(k)
    except NotImplementedError as err:
        print(err)
        return 1
    print("kappa undefined (the labels leave no room to disagree)" if k is None else f"kappa {k:.3f}")
    print("reread the guideline and the calibration reasons (kappa below 0.6)" if reread else "kappa is at least 0.6; kappa on 20 labels is noisy, so read it with the cells")
    dis = mod.disagreement_ids(ids, m, e)
    print(f"disagreements: {', '.join(dis) if dis else 'none'}")
    return 0


# ---------------------------------------------------------------------------------------------------------------------------
# judge-eval, choose, judge-probes

_STORE: Store | None = None


def store() -> Store:
    global _STORE
    if _STORE is None:
        _STORE = Store.load("judge")
    return _STORE


def verdict(judge: str, ticket: str, reply: str, trial: int = 1, **kw):
    """The recorded verdict of a judge on one reply. Raises NotRecorded when that request was never recorded."""
    key = build_request(judge, ticket, reply, **kw)["key"]
    try:
        return parse_verdict(store().lookup(key, trial)["output"])
    except ReplayMiss:
        raise NotRecorded(f"judge {judge} has no recording for this reply") from None


def split_verdicts(judge: str, split: str, **kw):
    items = labels.split_items(split)
    expert = labels.expert_labels()[0]
    ids, e, j, missing = [], [], [], []
    for it in items:
        try:
            v = verdict(judge, it["ticket"], it["reply"], **kw)
        except NotRecorded:
            missing.append(it["id"])
            continue
        ids.append(it["id"])
        e.append(expert[it["id"]])
        j.append(v)
    return ids, e, j, missing


def rates(judge: str, split: str, learner) -> dict:
    ids, e, j, missing = split_verdicts(judge, split)
    if missing:
        raise NotRecorded(f"not recorded yet: judge {judge} on {len(missing)} of {len(missing) + len(ids)} {split} replies")
    r = learner.tpr_tnr(e, j)
    r = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
    r.update(judge=judge, split=split, n=len(ids), label_source=labels.expert_labels()[2])
    return r


def fmt(r: dict) -> str:
    return (f"{r['judge']:7s} TPR {r['tpr']:.3f} ({r['tp']}/{r['tp'] + r['fn']})  TNR {r['tnr']:.3f} ({r['tn']}/{r['tn'] + r['fp']})  "
            f"tp {r['tp']} fn {r['fn']} tn {r['tn']} fp {r['fp']}")


def cmd_judge_eval(argv: list[str]) -> int:
    opt = lambda f, d=None: argv[argv.index(f) + 1] if f in argv else d  # noqa: E731
    if "--unlock" in argv:
        return unlock()
    split = opt("--split")
    if split not in ("dev", "test"):
        print("usage: judge-eval --judge J --split dev | judge-eval --all --split dev | judge-eval --split test | judge-eval --unlock")
        return 2
    try:
        learner = load_module(P2 / "judge_rule.py", "learner_judge_rule")
        if split == "test" and "--judge" not in argv:
            return run_test(learner)
        if "--all" in argv:
            return run_all_dev(learner)
        judge = canon(opt("--judge", ""))
        r = rates(judge, split, learner)
    except NotImplementedError as err:
        print(err)
        return 1
    except NotRecorded as err:
        print(err)
        return 1
    if split == "test":
        print("the test split is reported once, for the chosen judge: run `judge-eval --split test` after `choose`")
        return 2
    DEV_DIR.mkdir(parents=True, exist_ok=True)
    (DEV_DIR / f"{judge}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{split} split, {r['n']} replies ({r['tp'] + r['fn']} expert fails, {r['tn'] + r['fp']} expert passes). Fail is the positive class. {labels.source_line()}")
    print(fmt(r))
    print(f"wrote {(DEV_DIR / (judge + '.json')).relative_to(ROOT).as_posix()}")
    return 0


def allowed(r: dict) -> bool:
    return round(r["tpr"], 6) >= TPR_FLOOR


def run_all_dev(learner) -> int:
    rows = [rates(j, "dev", learner) for j in ALL_JUDGES]
    print(f"dev split, all {len(rows)} recorded judges. Fail is the positive class. {labels.source_line()}")
    for r in rows:
        print(fmt(r) + ("" if allowed(r) else "   (TPR under 0.85: the rule drops it)"))
    print(f"{sum(allowed(r) for r in rows)} of {len(rows)} judges have dev TPR of at least {TPR_FLOOR} and pass the rule's first step")
    return 0


def dev_rows() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(DEV_DIR.glob("*.json"))] if DEV_DIR.exists() else []


def cmd_choose(argv: list[str]) -> int:
    rows = dev_rows()
    if not rows:
        print("runs/judge-dev/ is empty: run `judge-eval --judge J --split dev` for your judges first")
        return 1
    learner = load_module(P2 / "judge_rule.py", "learner_judge_rule")
    try:
        chosen = learner.choose_judge(rows)
    except NotImplementedError as err:
        print(err)
        return 1
    if chosen is None:
        print("no judge has dev TPR of at least 0.85: run more judges, or tighten your labels")
        return 1
    row = next(r for r in rows if r["judge"] == chosen)
    (P2 / "choice.json").write_text(json.dumps({"judge": chosen, "dev": row, "judges_considered": sorted(r["judge"] for r in rows),
                                                 "label_source": row["label_source"]}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"considered {len(rows)} judges: {', '.join(sorted(r['judge'] for r in rows))}")
    print(f"choice: {chosen} (dev TPR {row['tpr']:.3f}, TNR {row['tnr']:.3f}); wrote {(P2 / 'choice.json').relative_to(ROOT).as_posix()}")
    return 0


def read_choice() -> dict | None:
    p = P2 / "choice.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if data.get("judge") else None


def run_test(learner) -> int:
    choice = read_choice()
    if not choice:
        print("no choice.json: run `python -m evalkit choose` first; the test split runs only for the judge the rule chose")
        return 1
    judge = choice["judge"]
    dev = next((r for r in dev_rows() if r["judge"] == judge), None)
    if dev is None or not allowed(dev):
        print(f"{judge} is not an allowed choice on dev (TPR under 0.85 or no dev file); choose again")
        return 1
    if LOCK.exists() and LOCK.read_text(encoding="utf-8").strip() != judge:
        print(f"refused: the test split was already reported for {LOCK.read_text(encoding='utf-8').strip()} ({LOCK.relative_to(ROOT).as_posix()}). "
              "Test is reported once. If that was a mistake, `python -m evalkit judge-eval --unlock` removes the lock and writes the reset to results.md.")
        return 1
    r = rates(judge, "test", learner)
    RUNS.mkdir(exist_ok=True)
    LOCK.write_text(judge + "\n", encoding="utf-8")
    (RUNS / "judge-test.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"test split, judge {judge}, {r['n']} replies ({r['tp'] + r['fn']} expert fails, {r['tn'] + r['fp']} expert passes). Fail is the positive class. {labels.source_line()}")
    print(fmt(r))
    d = dev
    print(f"dev for comparison: TPR {d['tpr']:.3f}, TNR {d['tnr']:.3f}; the choice was made among many judges on dev, so test is the honest number")
    print(f"wrote runs/judge-test.json and the lock runs/judge-test.lock ({judge})")
    return 0


def unlock() -> int:
    if not LOCK.exists():
        print("no lock to remove")
        return 0
    old = LOCK.read_text(encoding="utf-8").strip()
    LOCK.unlink()
    results = P2 / "results.md"
    text = results.read_text(encoding="utf-8") if results.exists() else ""
    head = "## Test lock resets"
    if head not in text:
        text = text.rstrip("\n") + f"\n\n{head}\n\n"
    text = text.rstrip("\n") + f"\n- {datetime.date.today().isoformat()}: removed the test lock for {old}\n"
    results.write_text(text, encoding="utf-8")
    print(f"removed the lock for {old} and recorded the reset in {results.relative_to(ROOT).as_posix()}")
    return 0


# --- probes -----------------------------------------------------------------------------------------------------------------

def flips(a: dict, b: dict) -> dict:
    ids = [i for i in a if i in b]
    return {"n": len(ids), "moved": sum(a[i] != b[i] for i in ids), "fail_to_pass": sum(a[i] == "fail" and b[i] == "pass" for i in ids),
            "pass_to_fail": sum(a[i] == "pass" and b[i] == "fail" for i in ids)}


def verdict_map(judge: str, items: list[dict], trial: int = 1, **kw) -> dict:
    out, missing = {}, 0
    for it in items:
        try:
            out[it["id"]] = verdict(judge, it["ticket"], it["reply"], trial=trial, **kw)
        except NotRecorded:
            missing += 1
    if missing:
        raise NotRecorded(f"not recorded yet: judge {judge} on {missing} of {len(items)} replies for this probe")
    return out


def second_model() -> str:
    return json.loads(SECOND.read_text(encoding="utf-8").splitlines()[0])["model"]


def probe_readings(judge: str) -> dict:
    dev = labels.split_items("dev")
    both = labels.split_items("dev") + labels.split_items("test")
    padded_ids = [r["id"] for r in labels.read_jsonl(PADDED_ITEMS)]
    by_id = {r["id"]: r for r in labels.label_set()}
    padded = [by_id[i] for i in padded_ids]
    out = {"judge": judge}
    v3_dev, v3_dev2 = verdict_map("v3", dev), verdict_map("v3", dev, trial=2)
    out["noise_flips_v3"] = flips(v3_dev, v3_dev2)
    v3_pad = verdict_map("v3", padded)
    out["noise_fail_to_pass_40"] = flips(v3_pad, verdict_map("v3", padded, trial=2))["fail_to_pass"]
    if HAS_EXAMPLES(judge):
        out["position"] = flips(verdict_map(judge, dev), verdict_map(judge, dev, reverse=True))
    else:
        out["position"] = None
    out["length"] = flips(verdict_map(judge, padded), verdict_map(judge, padded, padded=True))
    t1, t2 = verdict_map("v3", both), verdict_map("v3", both, trial=2)
    second = verdict_map("v3", both, model=second_model())
    rate = lambda m: 100 * sum(v == "pass" for v in m.values()) / len(m)  # noqa: E731
    out["selfpref"] = {"n": len(both), "v3_pass": round(rate(t1), 1), "second_pass": round(rate(second), 1),
                       "gap_points": round(abs(rate(t1) - rate(second)), 1), "noise_move_points": round(abs(rate(t1) - rate(t2)), 1)}
    return out


def cmd_probes(argv: list[str]) -> int:
    judge = canon(argv[argv.index("--judge") + 1]) if "--judge" in argv else None
    if not judge:
        print("usage: judge-probes --judge J")
        return 2
    try:
        r = probe_readings(judge)
    except NotRecorded as err:
        print(err)
        return 1
    nf = r["noise_flips_v3"]
    print(f"probes for judge {judge}. Every reading is read against the rerun reference, measured once on judge v3 (v3 run a second time, nothing changed).")
    print(f"rerun reference: {nf['moved']} of {nf['n']} dev verdicts moved on a plain rerun of v3 (fail to pass {nf['fail_to_pass']}, pass to fail {nf['pass_to_fail']}); "
          f"on the 40 padded replies {r['noise_fail_to_pass_40']} fails turned to pass")
    if r["position"] is None:
        print(f"position: not applicable (judge {judge} has no labelled examples to reverse)")
    else:
        p = r["position"]
        print(f"position: reversing the example order moved {p['moved']} of {p['n']} dev verdicts (fail to pass {p['fail_to_pass']}, pass to fail {p['pass_to_fail']}) "
              f"against {nf['moved']} for the rerun of v3")
    ln = r["length"]
    print(f"length: padding {ln['n']} replies with polite filler turned {ln['fail_to_pass']} fails into passes ({ln['moved']} verdicts moved) "
          f"against {r['noise_fail_to_pass_40']} for the rerun of v3")
    s = r["selfpref"]
    note = "" if judge == "v3" else f" (recorded for v3 only; shown here for v3, the judge every learner reads)"
    print(f"self-preference: the same-family judge v3 passes {s['v3_pass']}% of {s['n']} replies and the second-family judge passes {s['second_pass']}%: "
          f"gap {s['gap_points']} points against {s['noise_move_points']} points moved by the rerun of v3{note}")
    print("a count only a little above the rerun reference is not a finding; for judges other than v3 the reference is a rough guide")
    return 0


def main(command: str, argv: list[str]) -> int:
    return {"label": cmd_label, "kappa": cmd_kappa, "judge-eval": cmd_judge_eval, "choose": cmd_choose, "judge-probes": cmd_probes}[command](argv)


def label_main(argv):
    return main("label", argv)


def kappa_main(argv):
    return main("kappa", argv)


def judge_eval_main(argv):
    return main("judge-eval", argv)


def choose_main(argv):
    return main("choose", argv)


def probes_main(argv):
    return main("judge-probes", argv)
