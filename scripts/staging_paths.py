"""Print the paths the daily refresh must stage, one per line.

`refresh.yml` pipes this into `git add` instead of hard-coding the list. The list it used to
hard-code — `data/processed web/public/data` — omitted `docs/CURRENT_STATE.md` for forty-one
days while the build regenerated it and a test validated it on every single run. See
`pipeline/artifacts.py` for the full account.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.artifacts import commit_paths  # noqa: E402

if __name__ == "__main__":
    for p in commit_paths():
        print(p)
