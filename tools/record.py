"""Record model outputs once, with a live key. Author only; never run in a course step.

    python tools/record.py triage --variants A B --trials 5 --tickets datasets/pool/tickets.jsonl

Trial 1 of every case is sent directly and timed (latency_valid true). Trials 2 to 5 go through
the Message Batches API at half price (latency_valid false). Lines already recorded are skipped,
so the command can be stopped and run again. The key comes from the environment; it is never
printed or written.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from product import reply, triage  # noqa: E402

BUILDERS = {"triage": triage.build_request, "reply": reply.build_request}


def text_of(msg) -> str:
    return "".join(b.text for b in msg.content if b.type == "text")


def line(req, trial, feature, variant, msg, latency_ms, valid):
    return {
        "key": req["key"], "trial": trial, "feature": feature, "variant": variant,
        "model": msg.model, "recorded_at": date.today().isoformat(),
        "tokens_in": msg.usage.input_tokens, "tokens_out": msg.usage.output_tokens,
        "latency_ms": latency_ms, "latency_valid": valid,
        "stop_reason": msg.stop_reason, "output": text_of(msg),
    }


def create_args(req):
    return dict(model=req["model"], system=req["system"], messages=req["messages"], **req["params"])


def direct(client, req, tries=6):
    for attempt in range(tries):
        try:
            t0 = time.perf_counter()
            msg = client.messages.create(**create_args(req))
            return msg, round((time.perf_counter() - t0) * 1000)
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError):
            time.sleep(min(60, 2 ** attempt * 2))
    raise RuntimeError("direct call failed after retries")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feature", choices=BUILDERS)
    ap.add_argument("--variants", nargs="+", required=True)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--tickets", default="datasets/pool/tickets.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="first N tickets only (smoke test)")
    ap.add_argument("--direct-only", action="store_true")
    ap.add_argument("--batch-all", action="store_true", help="send trial 1 through the batch too (latency_valid false)")
    ap.add_argument("--day", type=int, nargs="*", default=[], help="only tickets with these day fields (traffic)")
    ap.add_argument("--tag", default="", help="write to <variant>-<tag>.jsonl")
    a = ap.parse_args()

    tickets = [json.loads(l) for l in (ROOT / a.tickets).read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.day:
        tickets = [t for t in tickets if t.get("day") in a.day]
    if a.limit:
        tickets = tickets[: a.limit]
    client = anthropic.Anthropic()
    folder = ROOT / "recordings" / a.feature
    folder.mkdir(parents=True, exist_ok=True)

    for variant in a.variants:
        path = folder / (f"{variant}-{a.tag}.jsonl" if a.tag else f"{variant}.jsonl")
        done = set()
        if path.exists():
            for l in path.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    r = json.loads(l)
                    done.add((r["key"], r["trial"]))
        reqs = [BUILDERS[a.feature](variant, t["text"]) for t in tickets]

        todo1 = [] if a.batch_all else [r for r in reqs if (r["key"], 1) not in done]
        print(f"{variant}: {len(todo1)} direct calls", flush=True)
        with ThreadPoolExecutor(max_workers=6) as pool, path.open("a", encoding="utf-8", newline="\n") as f:
            for req, (msg, ms) in zip(todo1, pool.map(lambda r: direct(client, r), todo1)):
                f.write(json.dumps(line(req, 1, a.feature, variant, msg, ms, True), ensure_ascii=False) + "\n")
                done.add((req["key"], 1))

        if a.direct_only or (a.trials < 2 and not a.batch_all):
            continue
        batch_reqs, meta = [], {}
        for i, req in enumerate(reqs):
            for trial in range(1 if a.batch_all else 2, a.trials + 1):
                if (req["key"], trial) in done:
                    continue
                cid = f"{variant}-{i}-{trial}"
                meta[cid] = (req, trial)
                batch_reqs.append(Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**create_args(req))))
        if not batch_reqs:
            continue
        print(f"{variant}: batch of {len(batch_reqs)}", flush=True)
        batch = client.messages.batches.create(requests=batch_reqs)
        while True:
            b = client.messages.batches.retrieve(batch.id)
            if b.processing_status == "ended":
                break
            time.sleep(60)
        failed = 0
        with path.open("a", encoding="utf-8", newline="\n") as f:
            for res in client.messages.batches.results(batch.id):
                if res.result.type != "succeeded":
                    failed += 1
                    continue
                req, trial = meta[res.custom_id]
                f.write(json.dumps(line(req, trial, a.feature, variant, res.result.message, None, False), ensure_ascii=False) + "\n")
        print(f"{variant}: batch done, {failed} not succeeded (run again to retry them)", flush=True)


if __name__ == "__main__":
    main()
