# AI Evals and Harnesses: reference repository (private)

The solved tree for the course "AI Evals and Harnesses" by Zeeshan Adil. The public learner template is made from this tree with `tools/make_starter.py`.

Never commit a key. Live recording (`tools/record.py`) reads the key from the environment and is for the author only; every course step runs in replay.

## Install and check

Python 3.11 or newer. From the repository root: `python -m venv .venv`, activate it, then `python -m pip install -e .`. The pins are in `pyproject.toml`: pytest 9.2.0, pydantic 2.14.2, PyYAML 6.0.2 (Inspect 0.3.287 is the optional `adopt` extra for chapter 6.9 only). Then `python -m evalkit doctor` prints four OK lines.

## Reference-only tools

`tools/make_results.py` runs the real commands of every challenge in replay and writes each `results.md`, the charts and `facts.json`. Run it after the recordings are frozen and before the tests: some tests read `runs/` and `datasets/mine/`, which the commands write. `tools/make_starter.py --check` builds the learner starter and checks that every test file passes here and fails there.
