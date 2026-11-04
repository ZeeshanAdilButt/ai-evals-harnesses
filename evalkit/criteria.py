"""The criteria checklist (2.6): `python -m evalkit criteria-check criteria/v1.md [--compare criteria/]`.

A criteria file has one section per criterion:

    ## 1. Short title
    Question: Does the reply ...?
    Pass example: ...
    Fail example: ...

The checklist: one question, answerable pass or fail, one pass and one fail example, no vague word.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRITERIA_DIR = ROOT / "criteria"
SHIPPED = CRITERIA_DIR / "shipped.md"
YES_NO_START = {"does", "is", "are", "did", "do", "has", "have", "can", "will", "would", "was", "were", "should", "could"}
VAGUE = {"good", "bad", "helpful", "nice", "appropriate", "great", "quality", "professional", "effective", "proper", "satisfactory"}
STOP = YES_NO_START | {"the", "a", "an", "to", "of", "and", "or", "in", "it", "its", "that", "this", "for", "with", "on", "as", "by", "at", "any", "not", "from"}


def parse_criteria(text: str) -> list[dict]:
    out = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        title, _, body = block.partition("\n")
        c = {"title": re.sub(r"^\d+\.\s*", "", title.strip()), "question": "", "pass": "", "fail": "", "applies": ""}
        key = None
        for line in body.splitlines():
            m = re.match(r"^(Question|Pass example|Fail example|Applies to):\s*(.*)$", line)
            if m:
                key = {"Question": "question", "Pass example": "pass", "Fail example": "fail", "Applies to": "applies"}[m.group(1)]
                c[key] = m.group(2).strip()
            elif key and line.strip():
                c[key] += " " + line.strip()
        out.append(c)
    return out


def problems(c: dict) -> list[str]:
    out = []
    q = c["question"]
    if not q:
        return ["no 'Question:' line"]
    if q.count("?") != 1 or not q.endswith("?"):
        out.append("write exactly one question, ending in one question mark")
    first = re.findall(r"[A-Za-z']+", q)[:1]
    if not first or first[0].lower() not in YES_NO_START:
        out.append("not answerable pass or fail: start with Does, Is, Are, Did or a similar yes or no word")
    vague = sorted({w for w in re.findall(r"[a-z]+", q.lower()) if w in VAGUE})
    if vague:
        out.append(f"vague word in the question: {', '.join(vague)}. Name the failure instead")
    if len(c["pass"].split()) < 5:
        out.append("write a pass example (at least 5 words)")
    if len(c["fail"].split()) < 5:
        out.append("write a fail example (at least 5 words)")
    return out


def content_words(q: str) -> set:
    return {w for w in re.findall(r"[a-z]+", q.lower()) if w not in STOP and len(w) > 2}


def overlap(a: str, b: str) -> float:
    x, y = content_words(a), content_words(b)
    return len(x & y) / len(x | y) if x | y else 0.0


def compare(mine: list[dict], shipped: list[dict]) -> list[str]:
    lines, used = [], set()
    for i, c in enumerate(mine, 1):
        best = max(range(len(shipped)), key=lambda j: overlap(c["question"], shipped[j]["question"]))
        o = overlap(c["question"], shipped[best]["question"])
        if o >= 0.25:
            used.add(best)
            lines.append(f"yours {i} ({c['title']}): about the same failure as shipped {best + 1} ({shipped[best]['title']}), overlap {o:.2f}")
        else:
            lines.append(f"yours {i} ({c['title']}): only in yours; the shipped criteria have no question about this")
    for j, s in enumerate(shipped, 1):
        if j - 1 not in used:
            lines.append(f"shipped {j} ({s['title']}): only in the shipped criteria; yours has no question about this")
    return lines


def main(argv: list[str]) -> int:
    args = list(argv)
    compare_dir = None
    if "--compare" in args:
        i = args.index("--compare")
        compare_dir = Path(args[i + 1]) if i + 1 < len(args) else CRITERIA_DIR
        del args[i:i + 2]
    path = Path(args[0]) if args else CRITERIA_DIR / "v1.md"
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        print(f"criteria-check: {path} is empty or missing. Write three criteria (see the part README).")
        return 1
    crit = parse_criteria(path.read_text(encoding="utf-8"))
    bad = 0
    if len(crit) != 3:
        print(f"criteria-check: write exactly three criteria (found {len(crit)})")
        bad += 1
    for i, c in enumerate(crit, 1):
        why = problems(c)
        if why:
            bad += 1
            print(f"criterion {i} ({c['title']}): FAILED")
            for w in why:
                print(f"  - {w}")
        else:
            print(f"criterion {i} ({c['title']}): OK")
    print("criteria-check: " + ("FAILED" if bad else "OK, all three pass the checklist"))
    if compare_dir is not None and not bad:
        shipped_path = compare_dir / "shipped.md" if compare_dir.is_dir() else compare_dir
        print(f"\ncompared with {shipped_path.name}:")
        for line in compare(crit, parse_criteria(shipped_path.read_text(encoding="utf-8"))):
            print("  " + line)
    return 1 if bad else 0
