"""Make the learner starter from this (reference) tree.

    python tools/make_starter.py --out C:\\starter          write the starter tree
    python tools/make_starter.py --check                    write it to a temp folder, run the challenge tests on
                                                            both trees: they must pass on the reference and fail
                                                            on the starter (every test file must have a failure)

Every block between `# YOUR TURN start: hint` and `# YOUR TURN end` becomes one line at the indent of the start marker:
`raise NotImplementedError("YOUR TURN: hint")` in a .py file, and the comment `# YOUR TURN: hint` in a .yml or .toml file (the gap stays visible).
Non-code starters: a results.md becomes its results.template.md (or a stub heading), my_flips.json becomes [], and the files in
RESET_PATHS (my_notes.jsonl, my_taxonomy.yaml, criteria/v1.md, my_dimensions.toml) become empty or stub files.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "runs", "__pycache__", ".pytest_cache", "local", "mine"}  # datasets/mine holds the reference learner's dataset v1
START = re.compile(r"^(\s*)# YOUR TURN start(?::\s*(.*))?$")
END = re.compile(r"^\s*# YOUR TURN end\s*$")
RESET_FILES = {"my_flips.json": "[]\n"}
# Files the learner fills in: the starter holds an empty or stub version of each (by path from the repo root).
RESET_PATHS = {
    "challenges/challenge-2-error-analysis/part-1-open-notes/my_notes.jsonl": "",
    "challenges/challenge-2-error-analysis/part-2-taxonomy-and-criteria/my_taxonomy.yaml": "",
    "criteria/v1.md": "",
    "challenges/challenge-5-labels-and-judges/part-1-labels-and-kappa/my_labels_calibration.jsonl": "",
    "challenges/challenge-5-labels-and-judges/part-1-labels-and-kappa/my_labels_blind.jsonl": "",
    "challenges/challenge-5-labels-and-judges/part-1-labels-and-kappa/reconcile.jsonl": "",
    "challenges/challenge-5-labels-and-judges/part-2-judge-comparison/choice.json": "{}\n",
    "challenges/challenge-9-ship-gates/part-1-gate-script/gate.toml": (
        "# The ship gate's numbers. Floors and budgets are the author's; margins are written by `gate --init-margin`.\n\n"
        "[floor]\ntriage = 0.85\nreply = 0.85\nagent = 0.80\n\n[budget]\ncost_per_1k = 2.5\np95_ms = 4500\n\n[margin]\n"),
    "challenges/challenge-3-dataset/part-1-dataset-v1/my_dimensions.toml": (
        "# My choices for dataset v1. Dimensions you can choose from: category, urgent, tone, language, length, source, easy.\n"
        'dimensions = ["category"]\nper_mix = 2\nheldout_share = 0.25\nseed = 7\ndedupe_threshold = 0.8\n\n[filters]\n\n[slices]\n'
        'delivery = { category = "delivery" }\n'),
}
# The author's recorded results and the private mentor keys: never in the starter.
EXCLUDE_TOP = {"reference", "facts.json"}
# Tools that hold the reference learner's answers: not part of the starter.
EXCLUDE = {"tools/make_ref_notes.py", "tools/make_results_c2_8.py", "tools/make_results_c5_11.py", "tools/standin_labels.py",
           ".github/workflows/gate.yml",                                           # the learner copies ci/workflow-starter.yml here in 9.9
           "challenges/challenge-11-capstone/part-1-release-suite/summary.json"}    # the learner's own run writes it


def strip_blocks(text: str, name: str = "", comment: bool = False) -> str:
    out, inside, indent = [], False, ""
    for line in text.splitlines():
        m = START.match(line)
        if m and not inside:
            inside, indent = True, m.group(1)
            hint = (m.group(2) or "fill in this block").replace('"', "'")
            out.append(f"{indent}# YOUR TURN: {hint}" if comment else f'{indent}raise NotImplementedError("YOUR TURN: {hint}")')
        elif inside:
            if END.match(line):
                inside = False
        else:
            out.append(line)
    if inside:
        raise SystemExit(f"{name}: YOUR TURN start without an end")
    return "\n".join(out) + "\n"


def build(dest: Path) -> int:
    if dest.exists():
        shutil.rmtree(dest)
    blocks = 0
    for src in sorted(ROOT.rglob("*")):
        rel = src.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) or src.is_dir():
            continue
        if src.suffix == ".pyc":
            continue
        to = dest / rel
        if rel.as_posix() in EXCLUDE or rel.parts[0] in EXCLUDE_TOP or (rel.parts[0] == "tools" and rel.name.startswith(("facts_", "check_pending"))):
            continue
        to.parent.mkdir(parents=True, exist_ok=True)
        if rel.as_posix() in RESET_PATHS:
            to.write_text(RESET_PATHS[rel.as_posix()], encoding="utf-8")
            continue
        if src.name in ("results.template.md", "report.template.md"):
            continue
        if src.name == "report.md" and "challenges" in rel.parts:
            to.write_text(src.with_name("report.template.md").read_text(encoding="utf-8"), encoding="utf-8")
            continue
        if src.name == "results.md" and "challenges" in rel.parts:
            template = src.with_name("results.template.md")
            body = template.read_text(encoding="utf-8") if template.exists() else f"# {src.parent.name}: results\n\nFill in after your run.\n"
            to.write_text(body, encoding="utf-8")
        elif src.name in RESET_FILES:
            to.write_text(RESET_FILES[src.name], encoding="utf-8")
        elif src.suffix in (".py", ".yml", ".toml"):
            text = src.read_text(encoding="utf-8")
            blocks += sum(1 for l in text.splitlines() if START.match(l))
            to.write_text(strip_blocks(text, str(rel), comment=src.suffix != ".py") if "YOUR TURN start" in text else text, encoding="utf-8")
        else:
            shutil.copy2(src, to)
    return blocks


def pytest(tree: Path):
    p = subprocess.run([sys.executable, "-m", "pytest", "challenges", "-q", "-p", "no:cacheprovider", "--tb=no", "-rfE"],
                       cwd=tree, capture_output=True, text=True)
    out = p.stdout
    passed = re.search(r"(\d+) passed", out)
    failed = re.search(r"(\d+) failed", out)
    errors = re.search(r"(\d+) error", out)
    files_failing = sorted({re.search(r"challenges/(\S+?)::", l.replace("\\", "/")).group(1) for l in out.splitlines()
                            if l.startswith(("FAILED", "ERROR")) and "::" in l})
    return (int(passed.group(1)) if passed else 0, int(failed.group(1)) if failed else 0,
            int(errors.group(1)) if errors else 0, files_failing, out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        dest = Path(tempfile.mkdtemp(prefix="evr-starter-")) / "starter"
        n = build(dest)
        print(f"starter written to {dest} ({n} YOUR TURN blocks stripped)")
        rp, rf, re_, _, rout = pytest(ROOT)
        sp, sf, se, files, sout = pytest(dest)
        all_test_files = sorted(str(p.relative_to(ROOT / "challenges")).replace("\\", "/") for p in (ROOT / "challenges").rglob("test_*.py"))
        print(f"reference: {rp} passed, {rf} failed, {re_} errors")
        print(f"starter:   {sp} passed, {sf} failed, {se} errors")
        print(f"test files failing on the starter: {len(files)} of {len(all_test_files)}")
        missing = [f for f in all_test_files if f not in files]
        ok = rf == 0 and re_ == 0 and rp > 0 and sf + se > 0 and not missing
        for f in missing:
            print(f"  NO failing test on the starter in {f}")
        print("starter check:", "OK" if ok else "FAILED")
        if not ok:
            print(rout[-1500:] if (rf or re_) else sout[-1500:])
        shutil.rmtree(dest.parent, ignore_errors=True)
        return 0 if ok else 1
    if not a.out:
        ap.error("--out or --check")
    n = build(Path(a.out))
    print(f"starter written to {a.out} ({n} YOUR TURN blocks stripped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
