"""Write ci/patches/regression.patch and harmless.patch: edits of product/prompts/reply_A.md that turn A's reply prompt into the
prompt of the variants ci-regression and ci-harmless (whose recordings ship in main). Run once; the output is committed.
`git apply` takes these patches on a branch made by `python -m evalkit make-ci-branches`."""
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "product" / "prompts"


def main():
    a = (P / "reply_A.md").read_text(encoding="utf-8").splitlines(keepends=True)
    for name, target in (("regression", "reply_ci_regression.md"), ("harmless", "reply_ci_harmless.md")):
        b = (P / target).read_text(encoding="utf-8").splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(a, b, "a/product/prompts/reply_A.md", "b/product/prompts/reply_A.md", n=3))
        (ROOT / "ci" / "patches" / f"{name}.patch").write_text(diff, encoding="utf-8", newline="\n")
        print(name, len(diff.splitlines()), "lines")


if __name__ == "__main__":
    main()
