"""`python -m evalkit gate ...` loads the learner's gate (challenges/challenge-9-ship-gates/part-1-gate-script/gate.py) and runs its main."""
from __future__ import annotations

from evalkit.judges_cli import load_module
from evalkit.suites import ROOT

GATE = ROOT / "challenges" / "challenge-9-ship-gates" / "part-1-gate-script" / "gate.py"


def gate_main(argv: list[str]) -> int:
    return load_module(GATE, "learner_gate").main(argv)
