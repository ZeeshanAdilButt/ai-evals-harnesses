"""`python -m evalkit make-ci-branches` (shipped, finished): make the two branches the CI challenge (9.9) needs.

A copy made from a GitHub template carries only the default branch. This command checks that the working tree is clean, then creates
`ci/regression` and `ci/harmless` from the branch you are on, applies one patch from ci/patches/ to each (both patches change only files
under product/prompts/), commits, returns you to your branch, and prints the two `git push` commands. It never pushes.

The recordings for both patched prompts are already in main (variants ci-regression and ci-harmless), so replay finds them by key.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCHES = (("ci/regression", "regression", "Regression for the CI challenge: the reply prompt no longer asks for a photo or an order number"),
            ("ci/harmless", "harmless", "Harmless change for the CI challenge: the reply prompt ends with a warmer sign-off"))
TARGET = "product/prompts/reply_A.md"


def git(root: Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8")
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {(p.stderr or p.stdout).strip()}")
    return p.stdout.strip()


def make_ci_branches(root: Path = ROOT, out=print) -> int:
    try:
        git(root, "rev-parse", "--is-inside-work-tree")
    except (RuntimeError, OSError):
        out("make-ci-branches: this folder is not a Git repository (clone your copy of the template first)")
        return 1
    if git(root, "status", "--porcelain"):
        out("make-ci-branches: the working tree is not clean. Commit or stash your changes first; no branch was made.")
        return 1
    start = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    existing = [b for b, _, _ in BRANCHES if git(root, "branch", "--list", b)]
    if existing:
        out(f"make-ci-branches: {', '.join(existing)} already exists. Delete it (git branch -D {existing[0]}) to make it again; nothing was changed.")
        return 1
    made = []
    try:
        for branch, patch, message in BRANCHES:
            git(root, "checkout", "-b", branch, start)
            git(root, "apply", str((root / "ci" / "patches" / f"{patch}.patch")))
            changed = git(root, "diff", "--name-only").splitlines()
            if changed != [TARGET]:
                raise RuntimeError(f"the {patch} patch changed {changed}, expected only {TARGET}")
            git(root, "add", "product/prompts")
            git(root, "commit", "-m", message)
            made.append(branch)
            git(root, "checkout", start)
    except RuntimeError as err:
        git(root, "checkout", start, check=False)
        out(f"make-ci-branches: {err}")
        return 1
    out(f"made {', '.join(made)} from {start}; you are back on {start}. Nothing was pushed.")
    out("Push both branches yourself:")
    out("  git push origin ci/regression ci/harmless")
    return 0


def main(argv: list[str]) -> int:
    return make_ci_branches()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
