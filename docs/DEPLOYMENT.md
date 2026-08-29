# Deployment — GitHub + Vercel

The deployed site is **static**. There is no server, no database, no API route and no
environment variable. The dataset ships as JSON files in `web/public/data/`, and the
map draws its own GeoJSON, so the running page makes zero external network requests.

**Repository:** https://github.com/Biomusician/russian-energy-dashboard (public)
**Deployment branch:** `main`
**Production URL:** https://russian-energy-dashboard.vercel.app

Architecture: **GitHub repo → daily GitHub Action rebuilds & commits the processed data →
push triggers a Vercel production deploy.** Vercel builds only the static frontend; it
never runs Python.

---

## 1. GitHub (done)

The repo exists and `main` is pushed. For reference, the one-time setup was:

```bash
gh repo create Biomusician/russian-energy-dashboard --public
git remote add origin https://github.com/Biomusician/russian-energy-dashboard.git
git push -u origin main
```

`data/raw/`, `tools/node/`, `node_modules/` and `web/dist/` are gitignored.
`data/processed/` and `web/public/data/` **are** committed — see §4 for why.

**Actions write permission** is already enabled (needed so the daily bot can push):

```bash
gh api -X PUT repos/Biomusician/russian-energy-dashboard/actions/permissions/workflow \
  -f default_workflow_permissions=write
```

Without it the daily commit step fails with a 403.

---

## 2. Connect Vercel (one-time, requires your Vercel login)

1. Go to **https://vercel.com/new** and sign in with **GitHub**.
2. If prompted, grant the Vercel GitHub App access to the `russian-energy-dashboard` repo.
3. **Import** `Biomusician/russian-energy-dashboard`.
4. On the configure screen:
   - **Root Directory:** leave it as the **repository root** (`./`). Do **not** set it to
     `web/` — the root `vercel.json` already does `cd web && npm install && npm run build`
     and outputs `web/dist`. Pointing the root at `web/` would bypass `vercel.json`.
   - **Framework Preset:** **Other** (set by `vercel.json`'s `framework: null`).
   - **Environment Variables:** none.
5. **Deploy.** Copy the production URL back into this file and the README.

`vercel.json` (repo root):

```jsonc
{
  "buildCommand": "cd web && npm install && npm run build",
  "outputDirectory": "web/dist",
  "framework": null,
  "headers": [ { "source": "/data/(.*)", "headers": [
    { "key": "Cache-Control", "value": "public, max-age=0, s-maxage=3600, stale-while-revalidate=86400" } ] } ]
}
```

If the dashboard shows *"could not load snapshot.json"*, `web/public/data/` was empty at
build time — run `.venv\Scripts\python.exe -m pipeline.run` locally and commit the result.

### Caching

`vercel.json` sets `s-maxage=3600, stale-while-revalidate=86400` on `/data/*`. The CDN
serves data for an hour, then refreshes in the background while still serving the old
copy. Since a fresh dataset arrives at most daily, this costs nothing in staleness and
removes almost all origin traffic. The HTML and hashed JS/CSS assets use Vercel's
defaults; a new deploy invalidates them.

Once connected, **every push to `main` auto-deploys** — including the daily data commits —
through Vercel's GitHub integration. No deploy hook or Vercel token lives in the repo.

---

## 3. Daily refresh workflow

`.github/workflows/refresh.yml` (`Refresh dataset`) runs at **05:20 UTC daily** and on
demand via **workflow_dispatch**. It:

1. Checks out the repo.
2. Sets up Python 3.13.
3. Restores the `data/raw` cache, then **rebuilds the dataset** (`python -m pipeline.run`).
4. **Runs the full test suite** (`python -m pytest`) — including the scope/coordinate
   gates and the dataset-sanity floor.
5. **Commits `data/processed/` + `web/public/data/` only if something substantive changed**,
   then pushes (which triggers the Vercel redeploy).

Two properties worth knowing:

- **Stdlib-only pipeline.** Nothing to install, so a scheduled run cannot fail because a
  wheel stopped publishing for Python 3.13. (Validated: it builds on the Ubuntu runner.)
- **It degrades rather than breaks.** `pipeline.util.fetch` retries with backoff and falls
  back to the cached copy with a warning, so a Wikipedia/Overpass outage produces
  yesterday's numbers, not an empty dashboard.

### No unnecessary commits

The emitted `snapshot.json` embeds a per-run wall-clock `build_time`, which would make the
Action commit on every run even when nothing changed. `scripts/ci_data_changed.py` compares
the freshly built data against `HEAD` with `build_time` stripped, and the workflow commits
**only when something substantive differs**. Legitimate daily drift (the date advancing,
the recency-weighted index decaying) still counts; a same-day rerun with no new data is
skipped. Bot commits read `data: daily refresh YYYY-MM-DD — ESDI x, N events`.

### Failure behavior — fail safe, never publish garbage

The steps run in order **build → test → commit**, and any non-zero step fails the job
*before* the commit step. So if an upstream source changes format, a parser breaks, a
scope/coordinate gate trips, or the sanity floor (min event count, non-zero ESDI, intact
denominators) fails, **the job goes red and nothing is committed or deployed** — the last
known-good public dataset stays live. A one-day-stale dashboard is preferable to a
silently corrupted one. Check the **Actions** tab; a red run is the signal.

### Force a manual refresh / deploy

- **Rebuild data now:** Actions → *Refresh dataset* → **Run workflow** (optionally tick
  **force_refresh** to ignore the `data/raw` cache). If the data changed, it pushes and
  Vercel redeploys.
- **Redeploy without data change:** Vercel dashboard → the project → **Redeploy**, or push
  any commit to `main`.

> GitHub disables scheduled workflows on repos with no activity for 60 days. For a
> low-traffic repo, push occasionally or trigger the workflow manually.

---

## 4. Why `data/processed/` is committed

It is a build artifact, which normally argues for gitignoring it. It is committed anyway
because **Vercel builds only the frontend** — it has no Python, and running the ETL inside
the Vercel build would add minutes to every deploy and make deploys depend on Overpass
being up.

The consequence to respect: a clean rebuild must stay deterministic given the same
upstream inputs. **Never hand-edit processed JSON.** Fix the curated source or the
pipeline, and rebuild. `data/curated/` is the truth; `data/processed/` is output. A
`.gitattributes` rule marks the emitted JSON `-diff merge=ours` so a machine-written
single-line file is never hand-merged.

---

## 5. Local development

```bash
.venv\Scripts\python.exe -m pipeline.run     # build the dataset
cd web && ..\scripts\npm.cmd run dev         # http://localhost:5178
```

`npm run build` runs `tsc -b` first, so a type error fails the build rather than shipping.
Node is portable under `tools/node/` (not on PATH); use `scripts\npm.cmd` / `scripts\node.cmd`.

---

## 6. Adding an event

1. Append a row to `data/curated/incidents.csv`. `source_urls` is required — a row without
   one is skipped with a warning.
2. If it hits an inventoried asset, set `linked_asset_id` to its `wri-*` / `osm-*` id from
   `assets.json` so the facility's capacity becomes the exposure base.
3. Rebuild, run `pytest`, commit, push. The daily Action would pick up curated changes too,
   but committing yourself deploys immediately.

Field definitions: [SCHEMA.md](SCHEMA.md).

---

## 7. Cost

Zero on free tiers. Static hosting, ~4 MB of data, one scheduled Action run per day
(~2–7 minutes depending on cache warmth). The only rate-limit risk is Overpass, which is
why queries are cached for 30 days, serialised, and paced 10 seconds apart.

---

## Iteration 5 note — new context data in the daily build

The daily `pipeline.run` now also fetches, in addition to the analytic OSM/WRI/Wikipedia/
Natural Earth sources:

- **Natural Earth 50m rivers** (`rivers.geojson`) — public domain, ~30-day cache.
- **The continental oil/gas trunk network** (`context_gas_network.geojson`,
  `context_oil_network.geojson`) from OSM/Overpass — four tiled queries, ~30-day cache.

These are **display-only context** and are marked `optional` in `data_manifest.json`; the
frontend **lazy-loads** them on first toggle, so a missing/late file never breaks the core
dashboard. The context-network build is **fail-safe**: if Overpass is unreachable on a
cache-less runner, it keeps the last committed network rather than emitting an empty file or
crashing the build — so a bad Overpass day degrades to yesterday's context, consistent with
the "one day stale beats bad data" rule.

Infrastructure-source cadence is honest: OSM/Natural Earth/GEM change monthly at most; only
the curated events and the daily rebuild timestamp move day to day. The GitHub Action still
skips a commit when only `build_time` changed (`scripts/ci_data_changed.py`).
