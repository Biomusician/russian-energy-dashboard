"""Give a git worktree the main checkout's untracked working files, by COPYING them (iteration 21).

    python scripts/link_worktree.py <worktree-path>

A worktree has the tracked files only. The frontend needs web/node_modules, the pipeline reads
data/raw, and some tests read the local review queue in data/candidates. Each is copied in.

NEVER LINK. The first version of this script made directory junctions, and removing the test
worktree with `git worktree remove --force` followed them and deleted the main checkout's
node_modules, data/raw, tools and the whole local review queue (2026-11-12). The queue was restored
from a sandbox copy; a link would make every automatic worktree cleanup a repeat of that. A copy
costs about 200 MB and cannot reach back into the main checkout.

The portable Node is not copied: run it from the main checkout's tools/node by absolute path.
The worktree's data/candidates is a snapshot. Never copy it back over the main queue.
"""
import shutil
import sys
from pathlib import Path

MAIN = Path(__file__).resolve().parent.parent
COPIES = ["web/node_modules", "data/raw", "data/candidates"]


def main():
    tree = Path(sys.argv[1]).resolve()
    if tree == MAIN:
        raise SystemExit("refusing: that is the main checkout")
    for rel in COPIES:
        src, dst = MAIN / rel, tree / rel
        if not src.exists():
            print(f"skip {rel}: not in the main checkout")
            continue
        shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=False)
        print(f"copied {rel}")


if __name__ == "__main__":
    main()
