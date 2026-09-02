"""Data quality, source freshness, and what the dashboard cannot tell you (iteration 11 §5).

WHY THIS IS EMITTED RATHER THAN WRITTEN IN REACT (addendum §14). Freshness statements written by
hand in a component are true on the day they are typed and silently false afterwards. "Generation
capacity from a 2018 census" stays on screen after the census is replaced; "retrieved today" stays
after the fetch stops running. So every statement here is derived at build time from the source
registry and the artefacts on disk, and a source with no date says it has none rather than
borrowing the build date.

THREE DATES THAT ARE ROUTINELY CONFLATED, and are kept apart:

    release        when the publisher issued this version. Often absent, and its absence is
                   itself a finding — GEM's map-data branch and the ENTSOG API both have no
                   release identifier at all, so neither can be cited as a dated publication.
    retrieved_at   when we fetched it. A GEM snapshot pulled today can still represent an older
                   tracker state; both are shown.
    content vintage what the data actually describes. The WRI power-plant base was frozen in
                   2022 and its newest Russian commissioning year is 2018 — a four-year gap
                   inside a single source.

The build date is none of these and is never used as a stand-in for any of them.

WHAT IS DELIBERATELY NOT DONE (addendum §15). No traffic light over the map, and no per-source
badge in the ribbon. The map keeps the four things a reader needs at a glance — whether a sector
is scored, what it divides by, whether a source is meaningfully old, and any explicit limitation
— and the full provenance lives in this view.
"""

import datetime as dt
import json

from pipeline.config import CURATED, ROOT, SECTORS
from pipeline.util import read_csv

# Age thresholds, applied only to a RETRIEVAL date. They are deliberately not applied to a
# content vintage: a structural census of power stations is not "stale news" at four years old
# the way an event feed would be, and colouring it as though it were would be the wrong alarm.
AGEING_DAYS = 45
STALE_DAYS = 180


def _parse_date(value):
    if not value:
        return None
    text = str(value).strip()[:10]
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def _split(value, sep="|"):
    return [p.strip() for p in (value or "").split(sep) if p.strip()]


def _evidence_dates(path):
    """(retrieved_at, how we know) for one source's evidence artefact.

    A manifest that states its own retrieval date is believed over the filesystem. Otherwise the
    cache file's modification time IS when we fetched it — honest, but labelled as such, because
    a fresh clone will show today for a file it has never actually downloaded.
    """
    if not path or not path.exists():
        return None, "absent", None
    release = None
    if path.suffix == ".json":
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            doc = None
        if isinstance(doc, dict):
            stated = doc.get("retrieved_at")
            if not stated:
                # Per-tracker manifests (GEM) nest one entry per tracker.
                for value in doc.values():
                    if isinstance(value, dict) and value.get("retrieved_at"):
                        stated = value["retrieved_at"]
                        break
            for value in doc.values():
                if isinstance(value, dict) and value.get("release"):
                    release = value["release"]
            if stated:
                return _parse_date(stated), "stated in the source manifest", release
    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).date()
    return mtime, "local cache file timestamp", release


def _freshness(retrieved, frozen, as_of):
    """Status for one source. `undated` is a real answer and the honest one for a live feed."""
    if frozen:
        return {
            "status": "frozen",
            "age_days": (as_of - frozen).days,
            "note": (f"Deliberately pinned at {frozen.isoformat()}. It does not go stale; it "
                     "describes a fixed moment, and that moment is the thing to judge."),
        }
    if not retrieved:
        return {"status": "undated", "age_days": None,
                "note": "No retrieval date is recorded for this source."}
    age = (as_of - retrieved).days
    status = "current" if age <= AGEING_DAYS else "ageing" if age <= STALE_DAYS else "stale"
    return {
        "status": status,
        "age_days": age,
        "note": (f"Retrieved {retrieved.isoformat()}, {age} day{'' if age == 1 else 's'} before "
                 f"this build's as-of date."),
    }


def load_registry():
    return read_csv(CURATED / "sources.csv")


def build_sources(as_of):
    """The structured source records the Data Quality view renders."""
    as_of_date = _parse_date(as_of) or dt.date.today()
    out = []
    for row in load_registry():
        evidence = ROOT / row["evidence_path"] if row.get("evidence_path") else None
        retrieved, basis, discovered_release = _evidence_dates(evidence)
        frozen = _parse_date(row.get("frozen_at"))
        release_id = row.get("release_identifier") or discovered_release or None
        out.append({
            "source_id": row["source_id"],
            "name": row["name"],
            "publisher": row["publisher"],
            "role": row["role"],
            "applies_to": {
                "sectors": _split(row.get("sectors")),
                "asset_classes": _split(row.get("asset_classes")),
            },
            "url": row.get("url") or None,
            "licence": row.get("licence") or None,
            "release_identifier": release_id,
            "release_expectation": row.get("release_expectation") or "live",
            "has_release_identifier": bool(release_id),
            # Three different situations that a single boolean would flatten into one. A tracker
            # that issues releases but was read from a live backend export is a real citation
            # problem; a continuously-edited wiki has no releases to miss; our own curated files
            # are versioned by this repository. Only the first is a finding.
            "citability": (
                "citable_release" if release_id else
                "internal_versioned_by_repo" if row.get("release_expectation") == "internal" else
                "snapshot_of_a_live_source" if row.get("release_expectation") == "live" else
                "release_expected_but_absent"),
            "content_vintage": row.get("content_vintage") or None,
            "retrieved_at": retrieved.isoformat() if retrieved else None,
            "retrieval_basis": basis,
            "frozen_at": frozen.isoformat() if frozen else None,
            "freshness": _freshness(retrieved, frozen, as_of_date),
            "limitations": _split(row.get("limitations")),
        })
    out.sort(key=lambda s: (s["role"], s["name"]))
    return out


def sector_states(snapshot, explanations):
    """The first thing §15 asks for: is this sector scored, experimental, or not scored at all.

    Read from what the build actually did rather than declared anywhere, so a sector that loses
    its denominator changes state on its own instead of keeping a stale label.
    """
    covered = set(snapshot.get("sectors_covered") or [])
    sectors = (explanations or {}).get("sectors") or {}
    states = []
    for s in SECTORS:
        entry = sectors.get(s) or {}
        mechanism = entry.get("mechanism")
        if s not in covered:
            state = "uncovered"
        elif mechanism == "event_burden":
            # Scored, but against a chosen constant rather than a measured base. Calling that
            # simply "scored" alongside a capacity share would flatten the difference that the
            # transmission proxy warning exists to preserve.
            state = "experimental"
        else:
            state = "scored"
        denominator = entry.get("denominator") or {}
        states.append({
            "sector": s,
            "state": state,
            "mechanism": mechanism,
            "value": entry.get("value"),
            "denominator_value": (round(denominator["value"], 1)
                                  if isinstance(denominator.get("value"), (int, float))
                                  else denominator.get("value")),
            "denominator_unit": denominator.get("unit"),
            "denominator_source": denominator.get("source"),
            "denominator_vintage": denominator.get("vintage"),
            "known_bias": denominator.get("known_bias"),
            "limitations": entry.get("limitations") or [],
            "proxy_warning": entry.get("proxy_warning"),
        })
    return states


def cannot_tell_you(snapshot, explanations):
    """The questions this dashboard cannot answer, derived from the build rather than asserted.

    Every entry is computed from a real figure in this build, so the list shrinks by itself when
    a gap is closed instead of outliving it. A hand-written version of this section is the one
    most certain to become false, because it is written once and describes a moving dataset.
    """
    items = []
    uncovered = snapshot.get("sectors_uncovered") or []
    if uncovered:
        items.append({
            "question": "How much gas or coal infrastructure is disrupted",
            "answer": (
                f"Not known. {', '.join(uncovered)} have no published capacity denominator, so "
                "they are excluded from the composite and their weight redistributed. Documented "
                "strikes in these sectors exist and are NOT scored. Excluded is not zero."),
            "basis": "sectors_uncovered",
        })

    total = snapshot.get("incident_total") or 0
    quantified = snapshot.get("incidents_with_quantified_capacity") or 0
    if total and quantified < total:
        items.append({
            "question": "How much capacity a given strike actually removed",
            "answer": (
                f"Not known for {total - quantified} of {total} events. Open reporting almost "
                "never states it, and nothing here fills that gap with an estimate. The index "
                "measures capacity AT disrupted sites — exposure, not loss."),
            "basis": "incidents_with_quantified_capacity",
        })

    coverage = snapshot.get("coverage") or {}
    if coverage.get("coverage_ratio") is not None:
        pct = round(coverage["coverage_ratio"] * 100)
        items.append({
            "question": "Every strike that has occurred",
            "answer": (
                f"No. {coverage.get('enumerated_in_this_dataset')} oil-sector strikes are "
                f"enumerated against a reported benchmark of "
                f"{coverage.get('reported_total_strikes')} ({pct}%). The remainder are counted "
                "in aggregate by the source without individual dates, so they cannot become "
                "events here. Other sectors have no benchmark at all."),
            "basis": "coverage",
        })

    sectors = (explanations or {}).get("sectors") or {}
    if (sectors.get("transmission") or {}).get("mechanism") == "event_burden":
        items.append({
            "question": "What fraction of the grid is offline",
            "answer": (
                "Not known, and this figure is not it. Transmission is scored as a weighted "
                "count of concurrent facility-events against a chosen saturation constant, not "
                "against any measure of grid capacity. The published sweep moves it roughly "
                "fourfold across plausible constants."),
            "basis": "transmission mechanism",
        })

    if (sectors.get("oil_logistics") or {}).get("basis") == "capacity_mtpa":
        items.append({
            "question": "What share of export terminal throughput is affected",
            "answer": (
                "Not known. Oil logistics has no published throughput denominator and borrows "
                "the refining capacity base as a proxy, so its value is a share of refining "
                "capacity — not of terminal throughput."),
            "basis": "oil_logistics denominator",
        })

    gen = (sectors.get("electric_generation") or {}).get("denominator") or {}
    if gen.get("known_bias"):
        items.append({
            "question": "The true current installed generating base",
            "answer": (
                f"Not known. The census vintage is {gen.get('vintage')}, and it "
                f"{gen.get('known_bias')}. The measured effect on the index is published in "
                "docs/GENERATION_DENOMINATOR_AUDIT.md."),
            "basis": "electric_generation denominator",
        })

    rs = snapshot.get("recovery_stats") or {}
    if rs.get("unresolved_count"):
        items.append({
            "question": "Whether a specific facility has actually been repaired",
            "answer": (
                f"Usually not. {rs['unresolved_count']} impairments have no observed resolution, "
                "so their decline over time is modelled decay, not evidence of repair. Where a "
                "restoration WAS observed, the record says so and the evidence kind travels with "
                "the number."),
            "basis": "recovery_stats",
        })

    # The scope boundary. Not a data gap that better sourcing would close — a deliberate limit,
    # and it belongs in the same list so a reader is never left wondering whether it is coming.
    items.append({
        "question": "Where units are, what is combat-ready, or what should be struck next",
        "answer": (
            "Out of scope by design and permanently so. This models publicly reported disruption "
            "to energy infrastructure aggregated to administrative region. It holds no unit "
            "positions, no readiness or fuel state, no vulnerability assessment of undamaged "
            "assets, and no targeting value of any kind. Events carry no coordinates."),
        "basis": "scope boundary",
    })
    return items


def build(snapshot, as_of):
    explanations = snapshot.get("explanations") or {}
    sources = build_sources(as_of)
    by_status = {}
    for s in sources:
        key = s["freshness"]["status"]
        by_status[key] = by_status.get(key, 0) + 1
    return {
        "as_of": as_of,
        "build_time": snapshot.get("build_time"),
        # Stated explicitly because the whole point of this view is that these are different
        # things: when the dashboard was built is not when anything in it was true.
        "build_date_is_not_a_source_date": (
            "The build date says when this page was generated. It says nothing about how old any "
            "source is. Each source below carries its own release, retrieval and content dates."),
        "sector_states": sector_states(snapshot, explanations),
        "sources": sources,
        "sources_by_freshness": by_status,
        # Only the publishers that DO issue releases and were nonetheless read without one.
        # Listing every undated wiki here would bury the two entries that actually matter.
        "sources_without_release_identifier": [
            s["source_id"] for s in sources if s["citability"] == "release_expected_but_absent"],
        "citability_note": (
            "A source read from a live feed is a snapshot taken on a date, not a publication "
            "issued on one. It cannot be cited as a dated release however recently it was read."),
        "cannot_tell_you": cannot_tell_you(snapshot, explanations),
    }
