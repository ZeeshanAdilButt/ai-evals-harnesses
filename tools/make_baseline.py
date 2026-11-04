"""Build baselines/full-A: variant A's results on the `full` suite, five trials, from A's recordings (replay only).

    .venv/Scripts/python.exe tools/make_baseline.py

A fresh CI runner needs no earlier run: the gate reads this folder. The file is byte-stable (no timings of the run are kept).
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit import engine, runner_reference  # noqa: E402


def main():
    tmp = ROOT / "runs" / "baseline-build"
    shutil.rmtree(tmp, ignore_errors=True)
    s = engine.run_suite("full", "A", impl=runner_reference, out=tmp)
    out = ROOT / "baselines" / "full-A"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tmp / "trials.jsonl", out / "trials.jsonl")
    (out / "meta.json").write_text(json.dumps({"suite": "full", "variant": "A", "trials": 5, "provider": "replay", "records": s["records"],
                                                "note": "variant A on the full suite from the recordings; read by `evalkit gate --baseline baselines/full-A`"},
                                               indent=1, sort_keys=True) + "\n", encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"baselines/full-A: {s['records']} trials, passed {s['passed']}, replay_miss {s['replay_miss']}")


if __name__ == "__main__":
    main()
