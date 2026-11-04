"""Print recorded outputs for writers (replay only, no network).

    python tools/show.py triage A t042          trials 1 to 5 of triage, variant A, ticket t042
    python tools/show.py reply B t042 --trial 2
    python tools/show.py agent A r12            the recorded runs of task r12 (trajectory, state, message)
    python tools/show.py ticket t042            the ticket with its labels and dimensions
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.replay import ReplayMiss, Store  # noqa: E402
from product import reply, triage  # noqa: E402


def ticket(tid):
    for f in ["datasets/pool/tickets.jsonl", "datasets/traffic/tickets.jsonl"]:
        for l in (ROOT / f).read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            if r["id"] == tid:
                return r
    raise SystemExit(f"no ticket {tid}")


def main():
    a = sys.argv[1:]
    trial = int(a[a.index("--trial") + 1]) if "--trial" in a else None
    if a[0] == "ticket":
        print(json.dumps(ticket(a[1]), ensure_ascii=False, indent=1))
        return
    if a[0] == "agent":
        for l in (ROOT / f"recordings/agent-runs/{a[1]}.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            if r["task"] == a[2] and (trial is None or r["trial"] == trial):
                print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    feature, variant, tid = a[0], a[1], a[2]
    t = ticket(tid)
    build = {"triage": triage.build_request, "reply": reply.build_request}[feature]
    key = build(variant, t["text"])["key"]
    store = Store.load(feature)
    for k in ([trial] if trial else range(1, 6)):
        try:
            rec = store.lookup(key, k)
            print(f"--- {feature} {variant} {tid} trial {k} ({rec['tokens_in']} in, {rec['tokens_out']} out, {rec['latency_ms']} ms)")
            print(rec["output"])
        except ReplayMiss:
            print(f"--- trial {k}: not recorded")


if __name__ == "__main__":
    main()
