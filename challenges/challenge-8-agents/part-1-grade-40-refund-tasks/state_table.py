"""Checkpoint 1: the state table of variant A. It uses only the shipped state grader."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit.graders.agent import grade_final_state, load_runs, load_tasks

tasks = load_tasks()
passes = {}
for trial in load_runs("A"):
    ok = grade_final_state(trial, tasks[trial["task"]])["ok"]
    passes[trial["task"]] = passes.get(trial["task"], 0) + int(ok)

failing = [t for t, c in sorted(passes.items()) if c < 5]
print(f"{len(passes)} tasks, 5 trials each; tasks below 5 of 5 on state: {', '.join(failing)}")
print("| task | state passes |")
print("|---|---|")
for t, c in sorted(passes.items()):
    print(f"| {t} | {c} |")
