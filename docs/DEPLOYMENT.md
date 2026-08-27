# Deployment — GitHub + Vercel

The deployed site is **static**. There is no server, no database, no API route and no
environment variable. The dataset ships as JSON files in `web/public/data/`, and the
map draws its own GeoJSON, so the running page makes zero external network requests.

That means deployment is: push to GitHub, connect to Vercel, done.

---

## 1. Push to GitHub

```bash
git remote add origin https://github.com/<you>/russian-energy-dashboard.git
git push -u origin main
```

`data/raw/` and `tools/node/` are gitignored. `data/processed/` **is** committed — see
§4 for why.

---

## 2. Connect Vercel

1. Vercel → **Add New… → Project** → import the repository.
2. Leave the root directory as the repository root. `vercel.json` handles the rest:

   ```jsonc
   {
     "buildCommand": "cd web && npm install && npm run build",
     "outputDirectory": "web/dist"
   }
   ```

3. Framework preset: **Other** (`vercel.json` sets `"framework": null`).
4. Deploy.

No environment variables are required. If the dashboard shows *"could not load
snapshot.json"*, `web/public/data/` was empty at build time — run `python -m
pipeline.run` locally and commit the result.

### Caching

`vercel.json` sets `s-maxage=3600, stale-while-revalidate=86400` on `/data/*`. The CDN
serves data for an hour, then refreshes in the background while still serving the old
copy. Since a fresh dataset arrives at most daily, this costs nothing in staleness and
removes almost all origin traffic.

---

## 3. Daily refresh

`.github/workflows/refresh.yml` runs at **05:20 UTC daily** (and on demand via
*workflow_dispatch*). It:

1. Rebuilds the dataset from Natural Earth, WRI, Overpass and Wikipedia.
2. Runs the test suite — including the scope tests.
3. Commits `data/processed/` and `web/public/data/` **only if something changed**.
4. Pushes, which triggers a Vercel redeploy.

Two properties worth knowing:

- **No dependencies to install.** The pipeline is stdlib-only, so a scheduled run
  cannot fail because a wheel stopped publishing for Python 3.13.
- **It degrades rather than breaks.** `pipeline/util.fetch` retries with backoff, and
  if a source is unreachable it falls back to the cached copy with a warning. A
  Wikipedia outage produces yesterday's numbers, not an empty dashboard.

`data/raw` is cached between runs, so a daily refresh re-fetches only what has expired
(Wikipedia every 12–24 h, Overpass and WRI every 30 days). Use **Run workflow →
force_refresh** to bypass it.

### Enable it

Repository → Settings → Actions → General → Workflow permissions → **Read and write
permissions**. Without this the commit step fails with a 403.

> GitHub disables scheduled workflows on repositories with no activity for 60 days.
> For a low-traffic repo, either push occasionally or trigger the workflow manually.

---

## 4. Why `data/processed/` is committed

It is a build artifact, which normally argues for gitignoring it. It is committed
anyway because **Vercel builds only the frontend** — it has no Python, and running the
ETL inside the Vercel build would add minutes to every deploy and make deploys depend
on Overpass being up.

The consequence to respect: a clean rebuild must stay deterministic given the same
upstream inputs. **Never hand-edit processed JSON.** Fix the curated source or the
pipeline, and rebuild. `data/curated/` is the truth; `data/processed/` is output.

---

## 5. Local development

```bash
.venv\Scripts\python.exe -m pipeline.run     # build the dataset
cd web && ..\scripts\npm.cmd run dev         # http://localhost:5178
```

`npm run build` runs `tsc -b` first, so a type error fails the build rather than
shipping.

---

## 6. Adding an event

1. Append a row to `data/curated/incidents.csv`. `source_urls` is required — a row
   without one is skipped with a warning.
2. If it hits an inventoried asset, set `linked_asset_id` to its `wri-*` / `osm-*` id
   from `assets.json` so the facility's capacity becomes the exposure base.
3. Rebuild, run `pytest`, commit.

Field definitions: [SCHEMA.md](SCHEMA.md).

---

## 7. Cost

Zero on free tiers. Static hosting, ~4 MB of data, one scheduled Action run per day
(~2 minutes). The only rate-limit risk is Overpass, which is why queries are cached for
30 days, serialised, and paced 10 seconds apart.
