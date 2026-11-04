"""Make one synthetic week of production traffic (module 10). Author only; one batch call.

    python tools/make_traffic.py spec      write datasets/traffic/spec.jsonl (3,500 rows, seed 11)
    python tools/make_traffic.py generate  write the ticket texts with the cheaper model (Batches API)
    python tools/make_traffic.py build     scrub and write datasets/traffic/tickets.jsonl

Each row has a day (1 to 7), the dimensions, and the expected labels. The ticket text is written
by the cheaper model to the row's dimensions and scrubbed with the shipped scrubber. 30% of
tickets are refund tickets, so about 150 refund replies a day can be judged.
"""
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "datasets" / "traffic"
CATS = ["billing", "delivery", "refund", "account", "product"]


def spec():
    rng = random.Random(11)
    rows = []
    for day in range(1, 8):
        for i in range(500):
            cat = rng.choices(CATS, weights=[15, 25, 30, 15, 15])[0]
            rows.append({"id": f"d{day}-{i + 1:03d}", "day": day, "category": cat,
                         "urgent": rng.random() < 0.08,
                         "tone": rng.choices(["calm", "angry", "confused"], weights=[5, 3, 2])[0],
                         "language": rng.choices(["english", "mixed"], weights=[7, 3])[0],
                         "length": rng.choices(["short", "normal", "long"], weights=[3, 5, 2])[0],
                         "pii": rng.random() < 0.2})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "spec.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    print(len(rows))


GUIDE = {"billing": "a charge, payment method, promo code or double charge", "delivery": "a late, missing or wrong delivery, the delivery slot or the driver",
         "refund": "getting money back, or asking where a refund is", "account": "login, password, email, address or deleting the account",
         "product": "an item, stock, quality, ingredients or allergens"}
LEN = {"short": "under 15 words", "normal": "between 20 and 70 words", "long": "between 90 and 140 words"}


def prompt(r):
    lang = ("Write mostly in English but mix in a few words or a short phrase of Spanish, Hindi or Urdu written in Latin letters, the way a real customer might."
            if r["language"] == "mixed" else "Write in English.")
    urgent = ("The customer is harmed or blocked today (for example spoiled food someone ate, today's delivery missing, a payment that stops an order, or being locked out)."
              if r["urgent"] else "Nothing about it is urgent today.")
    pii = "Include one fake email ending in @example.com or one fake phone number of the form 555-01NN." if r["pii"] else "Do not include any email address or phone number."
    return (f"Write one message a customer sends to the support team of FreshMarket, an online grocery store. It is about {GUIDE[r['category']]}. "
            f"{urgent} Tone: {r['tone']}. Length: {LEN[r['length']]}. {lang} {pii} Use an order number like FM-123456 if it fits. "
            "Vary the items and details. Do not use em dashes or en dashes. Reply with the message text only.")


def generate():
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    rows = [json.loads(l) for l in (OUT / "spec.jsonl").read_text(encoding="utf-8").splitlines()]
    have = set()
    tf = OUT / "text.jsonl"
    if tf.exists():
        have = {json.loads(l)["id"] for l in tf.read_text(encoding="utf-8").splitlines() if l.strip()}
    todo = [r for r in rows if r["id"] not in have]
    client = anthropic.Anthropic()
    reqs = [Request(custom_id=r["id"], params=MessageCreateParamsNonStreaming(
        model="claude-haiku-5-5", max_tokens=400, thinking={"type": "disabled"}, output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt(r)}])) for r in todo]
    print("batch", len(reqs), flush=True)
    b = client.messages.batches.create(requests=reqs)
    while client.messages.batches.retrieve(b.id).processing_status != "ended":
        time.sleep(30)
    tin = tout = 0
    with tf.open("a", encoding="utf-8", newline="\n") as f:
        for res in client.messages.batches.results(b.id):
            if res.result.type != "succeeded":
                continue
            m = res.result.message
            tin += m.usage.input_tokens; tout += m.usage.output_tokens
            text = "".join(x.text for x in m.content if x.type == "text").strip()
            f.write(json.dumps({"id": res.custom_id, "raw_text": text}, ensure_ascii=False) + "\n")
    print("tokens", tin, tout, "cost about $%.2f" % ((tin * 0.10 + tout * 0.50) / 1e6 / 2), flush=True)


def build():
    from evalkit.scrub import scrub_text
    rows = {r["id"]: r for r in map(json.loads, (OUT / "spec.jsonl").read_text(encoding="utf-8").splitlines())}
    texts = {t["id"]: t["raw_text"] for t in map(json.loads, (OUT / "text.jsonl").read_text(encoding="utf-8").splitlines()) if t.get("raw_text")}
    out = []
    for i, r in sorted(rows.items()):
        if i not in texts:
            continue
        r = dict(r); r["raw_text"] = texts[i].replace("—", ", ").replace("–", " to "); r["text"] = scrub_text(r["raw_text"])
        r["expected"] = {"category": r["category"], "urgent": r["urgent"]}
        out.append(r)
    (OUT / "tickets.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out), encoding="utf-8")
    print(len(out), "of", len(rows))


if __name__ == "__main__":
    {"spec": spec, "generate": generate, "build": build}[sys.argv[1]]()
