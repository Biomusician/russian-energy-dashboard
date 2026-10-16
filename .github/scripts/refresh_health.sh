#!/usr/bin/env bash
# Turn a persistent scheduled-refresh failure into one open issue, and close it on recovery.
#
# WHY. Between 2026-09-21 and 2026-10-01 the scheduled refresh failed eleven consecutive times
# and the live dashboard served eleven-day-old figures. GitHub emails the repository owner on the
# FIRST failure of a scheduled workflow and then goes quiet, so there was exactly one
# notification for an eleven-day outage, on day one, in a mailbox.
#
# Deliberately not on the first failure: a transient upstream 503 is not worth an issue. Two
# consecutive failures means a day has already been lost and the cause is unlikely to be
# transient.
#
# Uses only `gh`, which is preinstalled on GitHub-hosted runners, so the scheduled job stays
# toolchain-free.

set -euo pipefail

REPO="${GITHUB_REPOSITORY}"
LABEL="refresh-failure"
TITLE="Scheduled dataset refresh is failing"

# `gh` needs the label to exist before it can filter on it. Idempotent.
gh label create "$LABEL" --repo "$REPO" --color B60205 \
  --description "The daily dataset refresh has failed repeatedly" 2>/dev/null || true

existing="$(gh issue list --repo "$REPO" --label "$LABEL" --state open \
             --json number --jq '.[0].number // empty')"

if [ "${REFRESH_RESULT}" = "success" ]; then
  if [ -n "$existing" ]; then
    gh issue comment "$existing" --repo "$REPO" \
      --body "Recovered: the scheduled refresh succeeded in [run ${GITHUB_RUN_ID}](https://github.com/${REPO}/actions/runs/${GITHUB_RUN_ID}). Closing."
    gh issue close "$existing" --repo "$REPO"
    echo "closed #$existing"
  else
    echo "healthy, nothing open"
  fi
  exit 0
fi

# Count consecutive failures, most recent first, over scheduled runs of this workflow only.
# A manual workflow_dispatch failure while debugging must not count toward the streak.
streak="$(gh run list --repo "$REPO" --workflow "Refresh dataset" --event schedule \
            --limit 12 --json conclusion --jq \
            '[.[] | .conclusion] | (index("success") // length)')"

echo "consecutive scheduled failures: $streak"
if [ "$streak" -lt 2 ]; then
  echo "one failure only — not opening an issue"
  exit 0
fi

body="The scheduled \`Refresh dataset\` workflow has failed **${streak}** times in a row.

Latest run: https://github.com/${REPO}/actions/runs/${GITHUB_RUN_ID}

While this is failing the dashboard keeps serving the last successfully committed payload. It
says so itself — the staleness notice appears once the build is older than the cadence declared
in \`pipeline/config.py\` — but the data is not being updated.

**Check the build step first, then the test step.** The eleven-day outage in September 2026 was
a test whose assertion was false, not a broken pipeline: every one of those eleven runs built the
dataset correctly and then discarded it. If the build step is green and the test step is red,
read the failing assertion before touching the pipeline.

This issue is opened by \`.github/scripts/refresh_health.sh\` after two consecutive scheduled
failures, updated on each subsequent one, and closed automatically on the first success."

if [ -n "$existing" ]; then
  gh issue comment "$existing" --repo "$REPO" --body "$body"
  echo "updated #$existing"
else
  gh issue create --repo "$REPO" --title "$TITLE" --label "$LABEL" --body "$body"
  echo "opened a new issue"
fi
