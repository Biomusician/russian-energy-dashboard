"""Link a git worktree to the main checkout's untracked toolchain (iteration 21).

    python scripts/link_worktree.py <worktree-path>

A worktree has the tracked files only. The frontend needs web/node_modules, the pipeline reads
data/raw, the local review queue is data/candidates, and the portable Node lives in tools/. Each is
linked as a Windows directory junction, so nothing is copied and the main checkout stays the one
place they live. Run from the main checkout. Treat data/candidates as read-only from a worktree.
"""
import subprocess
import sys
from pathlib import Path

MAIN = Path(__file__).resolve().parent.parent
LINKS = ["web/node_modules", "data/raw", "data/candidates", "tools"]


def main():
    tree = Path(sys.argv[1]).resolve()
    for rel in LINKS:
        src, dst = MAIN / rel, tree / rel
        if not src.exists():
            print(f"skip {rel}: not in the main checkout")
            continue
        if dst.exists():
            # A tracked README can make data/candidates exist already; only an empty or README-only
            # directory is replaced by the link.
            if dst.is_dir() and all(p.name == "README.md" for p in dst.iterdir()):
                for p in dst.iterdir():
                    p.unlink()
                dst.rmdir()
            else:
                print(f"keep {rel}: already present")
                continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], check=True, capture_output=True)
        print(f"linked {rel}")


if __name__ == "__main__":
    main()
