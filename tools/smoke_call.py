"""One triage call, printed without any credential. Author check only."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
print("start", flush=True)
import anthropic
print("sdk", anthropic.__version__, flush=True)
from product import triage
t = json.loads((ROOT / "datasets/pool/tickets.jsonl").read_text(encoding="utf-8").splitlines()[0])
req = triage.build_request("A", t["text"])
client = anthropic.Anthropic()
t0 = time.perf_counter()
msg = client.messages.create(model=req["model"], system=req["system"], messages=req["messages"], **req["params"])
print("ms", round((time.perf_counter() - t0) * 1000), "stop", msg.stop_reason, "in", msg.usage.input_tokens, "out", msg.usage.output_tokens, flush=True)
print("model", msg.model, flush=True)
print("text", "".join(b.text for b in msg.content if b.type == "text"), flush=True)
print("expected", t["expected"], flush=True)
