"""Record a second-family judge (another model family, for the 5.6 self-preference probe) by
calling a command-line model tool once per item with the judge v3 prompt. Author only.

    python tools/record_second_judge.py --items datasets/labels/judge_items.jsonl --model gemini-4-argon-medium

The tool reads one prompt file per call from a scratch folder and prints the JSON verdict. Each
line is keyed like any recording (model id, system, messages), with tokens unknown (null).
"""
import argparse
import json
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from product.judge import build_request  # noqa: E402

lock = threading.Lock()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--model", default="gemini-4-argon-medium")
    ap.add_argument("--judges", nargs="+", default=["v3"])
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    items = [json.loads(l) for l in (ROOT / a.items).read_text(encoding="utf-8").splitlines() if l.strip()]
    out = ROOT / "recordings" / "judge"
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for j in a.judges:
        path = out / f"{j}-second.jsonl"
        done = set()
        if path.exists():
            done = {json.loads(l)["key"] for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
        for it in items:
            req = build_request(j, it["ticket"], it["reply"], model=a.model)
            if req["key"] not in done:
                jobs.append((j, it, req, path))
    print(len(jobs), "calls", flush=True)

    def one(job):
        j, it, req, path = job
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "prompt.txt").write_text(req["system"] + "\n\n" + req["messages"][0]["content"], encoding="utf-8")
            t0 = time.perf_counter()
            r = subprocess.run(["agy", "--model", a.model, "--print-timeout", "300s", "-p",
                                "Read prompt.txt in the current folder. It is a grading task. Answer it exactly as it asks, with the JSON object only."],
                               cwd=d, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=600)
            ms = round((time.perf_counter() - t0) * 1000)
        line = {"key": req["key"], "trial": 1, "feature": "judge", "variant": f"{j}-second", "item": it["id"],
                "model": a.model, "recorded_at": date.today().isoformat(), "tokens_in": None, "tokens_out": None,
                "latency_ms": ms, "latency_valid": False, "stop_reason": "end_turn" if r.returncode == 0 else "error",
                "output": r.stdout.strip()}
        with lock, path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(one, jobs))
    print("done", flush=True)


if __name__ == "__main__":
    main()
