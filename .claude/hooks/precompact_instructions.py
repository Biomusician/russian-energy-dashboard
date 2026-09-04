"""Feed the project's compaction rules into every compaction, automatic or manual.

WHY THIS EXISTS. `/compact` accepts custom instructions when a human types them, but an
AUTOMATIC compaction has no one there to type anything — and an automatic compaction is exactly
the one that happens unattended, deep into a long session, when the context most needs careful
pruning. Without this, an auto-compact would summarise this project with generic instructions and
could quietly drop the rules that make its numbers honest.

The PreCompact hook fires before either kind, so the same rules apply to both.

Reads .claude/commands/compact.md, strips its YAML frontmatter, and emits it as the hook's
additionalContext. Keeping the prose in the command file means there is ONE copy: editing
/compact also changes what an automatic compaction is told.

Stdout must be JSON and nothing else — anything else here becomes hook noise on every compaction.
"""

import io
import json
import os
import re
import sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
RULES = os.path.join(ROOT, ".claude", "commands", "compact.md")


def main() -> int:
    try:
        # encoding= is not optional on this machine: the default is cp1252 and this repo is full
        # of Cyrillic and en-dashes.
        text = io.open(RULES, encoding="utf-8").read()
    except OSError:
        # A missing rules file must not break compaction. Emitting nothing lets the default
        # summariser run, which is worse than these rules but far better than a failed compact.
        return 0

    # Drop the frontmatter; the summariser needs the prose, not the slash-command metadata.
    text = re.sub(r"\A---.*?\n---\s*", "", text, count=1, flags=re.S)

    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext":
                "Compaction instructions for this repository — follow them in addition to the "
                "default summarisation:\n\n" + text,
        },
    }, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
