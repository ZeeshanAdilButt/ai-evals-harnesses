"""Record judge verdicts on refund replies through the Batches API. Author only.

    python tools/record_judge.py --items datasets/labels/judge_items.jsonl --judges v1 v2 v3 [--reverse] [--padded] [--trial 1]

Items are {"id", "ticket", "reply"}. Every request goes in one batch (latency_valid false; judge
latency is not taught). Lines go to recordings/judge/<judge>[-rev][-pad].jsonl; recorded
(key, trial) pairs are skipped.
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from product.judge import build_request  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--judges", nargs="+", required=True)
    ap.add_argument("--reverse", action="store_true")
    ap.add_argument("--padded", action="store_true")
    ap.add_argument("--trial", type=int, default=1)
    ap.add_argument("--model", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    items = [json.loads(l) for l in (ROOT / a.items).read_text(encoding="utf-8").splitlines() if l.strip()]
    folder = ROOT / "recordings" / "judge"
    folder.mkdir(parents=True, exist_ok=True)
    reqs, meta = [], {}
    for j in a.judges:
        name = j + ("-rev" if a.reverse else "") + ("-pad" if a.padded else "") + ("-second" if a.model else "")
        path = folder / f"{name}.jsonl"
        done = set()
        if path.exists():
            done = {(r["key"], r["trial"]) for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r}
        for it in items:
            kw = {"reverse": a.reverse, "padded": a.padded}
            if a.model:
                kw["model"] = a.model
            req = build_request(j, it["ticket"], it["reply"], **kw)
            if (req["key"], a.trial) in done:
                continue
            cid = f"{len(reqs)}"
            meta[cid] = (req, path, name, it["id"])
            reqs.append(Request(custom_id=cid, params=MessageCreateParamsNonStreaming(
                model=req["model"], system=req["system"], messages=req["messages"], **req["params"])))
    print(f"{len(reqs)} judge calls", flush=True)
    if a.dry_run or not reqs:
        return
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=reqs)
    while client.messages.batches.retrieve(batch.id).processing_status != "ended":
        time.sleep(30)
    failed = 0
    files = {}
    for res in client.messages.batches.results(batch.id):
        if res.result.type != "succeeded":
            failed += 1
            continue
        req, path, name, item_id = meta[res.custom_id]
        m = res.result.message
        line = {"key": req["key"], "trial": a.trial, "feature": "judge", "variant": name, "item": item_id,
                "model": m.model, "recorded_at": date.today().isoformat(), "tokens_in": m.usage.input_tokens,
                "tokens_out": m.usage.output_tokens, "latency_ms": None, "latency_valid": False,
                "stop_reason": m.stop_reason, "output": "".join(b.text for b in m.content if b.type == "text")}
        files.setdefault(path, []).append(json.dumps(line, ensure_ascii=False))
    for path, lines in files.items():
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
    print(f"done, {failed} not succeeded (run again to retry)", flush=True)


if __name__ == "__main__":
    main()
