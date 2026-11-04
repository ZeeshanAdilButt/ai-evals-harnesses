"""The label set and the expert's labels (shipped, finished).

datasets/labels/label_set.jsonl holds 190 refund replies with the drafts of the expert's label and reason, split into calibration (10),
blind (20), dev (80) and test (80). When the author has confirmed the labels they are in datasets/labels/expert_labels.jsonl
({"id", "verdict", optionally "reason"}); that file wins over the drafts. Every results file says which source it used.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "datasets" / "labels"
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def read_jsonl(path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def label_set() -> list[dict]:
    return read_jsonl(LABELS / "label_set.jsonl")


def expert_labels() -> tuple[dict, dict, str]:
    """(verdicts by id, reasons by id, source): source is "confirmed" when expert_labels.jsonl exists, else "draft"."""
    rows = label_set()
    confirmed = LABELS / "expert_labels.jsonl"
    if confirmed.exists():
        got = {r["id"]: r for r in read_jsonl(confirmed)}
        verdicts = {r["id"]: got[r["id"]]["verdict"] for r in rows}
        reasons = {r["id"]: got[r["id"]].get("reason", r["draft_reason"]) for r in rows}
        return verdicts, reasons, "confirmed"
    return {r["id"]: r["draft_verdict"] for r in rows}, {r["id"]: r["draft_reason"] for r in rows}, "draft"


def split_items(split: str) -> list[dict]:
    return [r for r in label_set() if r["split"] == split]


def source_line() -> str:
    src = expert_labels()[2]
    return ("Expert labels: drafted by a model and accepted by the author as drafted, not individually reviewed; the author changed one (datasets/labels/expert_labels.jsonl)." if src == "confirmed"
            else "Expert labels: DRAFT labels (a model's first pass, not yet confirmed by the author); the numbers will move when the author confirms.")
