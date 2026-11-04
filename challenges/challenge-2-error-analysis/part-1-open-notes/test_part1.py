"""Challenge 2, part 1. One test file: test_thirty_clean_notes fails until my_notes.jsonl holds 30 clean notes.
There is no code to write, so there are no checkpoints."""
import json
from pathlib import Path

from evalkit import notes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def test_notes_check_flags_short_and_vague_notes():
    assert notes.problems("bad reply") == ["under 8 words (2)", "names no failure"]
    assert any("names no failure" in p for p in notes.problems("This reply is just not very nice to read at all really"))
    assert notes.problems("Says the customer is inside the 7 day window with no delivery date given.") == []
    assert notes.problems("No failure found. The reply states only what the policy says and asks for a photo.") == []


def test_timing_warns_under_25_seconds():
    fast = [{"trace_id": f"tr{i:02d}", "note": "x", "seconds": 12.0} for i in range(1, 6)]
    slow = [{"trace_id": f"tr{i:02d}", "note": "x", "seconds": 60.0} for i in range(1, 6)]
    assert "WARNING" in notes.timing_line(fast)
    assert "WARNING" not in notes.timing_line(slow)


def test_thirty_clean_notes():
    path = HERE / "my_notes.jsonl"
    rows = notes.read_notes(path)
    assert len(rows) == 30, f"my_notes.jsonl holds {len(rows)} notes: write one for each of tr01 to tr30"
    assert [r["trace_id"] for r in rows] == notes.LEARNER_TRACES, "one note per trace, tr01 to tr30, in order"
    for r in rows:
        why = notes.problems(r["note"])
        assert not why, f"{r['trace_id']} is flagged ({'; '.join(why)}): rewrite it"
        assert isinstance(r["seconds"], (int, float)) and r["seconds"] > 0, f"{r['trace_id']}: seconds must be a positive number"
    author = {json.loads(l)["note"] for l in (ROOT / "datasets/traces/author_notes.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    assert not author & {r["note"] for r in rows}, "your notes are your own words, not the author's"
    assert len({r["note"] for r in rows}) == 30, "two traces have the same note"


def test_results_written():
    body = (HERE / "results.md").read_text(encoding="utf-8")
    assert PLACEHOLDER not in body, "results.md still has '(fill in)'"
    assert "Median seconds per trace:" in body and "Words I reused:" in body
