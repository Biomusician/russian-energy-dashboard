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
import subprocess

from pipeline.config import CURATED, ROOT, SECTORS
from pipeline.util import read_csv

# How we came to believe a retrieval date. This is a closed vocabulary because the difference
# matters: a local cache file's modification time is OUR filesystem's opinion, and must never be
# rendered in a way that reads as the publisher's freshness. On a fresh clone it says today for a
# file that was never downloaded.
RETRIEVAL_MANIFEST = "manifest_stated"
RETRIEVAL_HTTP = "http_source_metadata"
RETRIEVAL_CACHE_MTIME = "local_cache_mtime"
RETRIEVAL_COMMIT = "repo_commit_timestamp"
RETRIEVAL_UNKNOWN = "unknown"

RETRIEVAL_LABEL = {
    RETRIEVAL_MANIFEST: "stated by the source manifest",
    RETRIEVAL_HTTP: "from HTTP response metadata",
    RETRIEVAL_CACHE_MTIME: "local cache file timestamp - our filesystem, not the publisher",
    RETRIEVAL_COMMIT: "when the record last changed in this repository",
    RETRIEVAL_UNKNOWN: "not recorded",
}

# Whether a retrieval date says anything at all about the PUBLISHER. Only a manifest or HTTP
# date does; the other two describe this repository.
RETRIEVAL_IS_PUBLISHER_SIGNAL = {
    RETRIEVAL_MANIFEST: True,
    RETRIEVAL_HTTP: True,
    RETRIEVAL_CACHE_MTIME: False,
    RETRIEVAL_COMMIT: False,
    RETRIEVAL_UNKNOWN: False,
}

# Index participation and methodological basis are INDEPENDENT (addendum §1). Collapsing them
# into one ladder made transmission read as excluded from the headline when it is in fact scored
# in it — the single most consequential thing this view could get wrong.
PARTICIPATION_SCORED = "scored"
PARTICIPATION_NOT_SCORED = "not_scored"

BASIS_CAPACITY = "capacity_based"
BASIS_PROXY_CAPACITY = "proxy_capacity_base"
BASIS_EVENT_BURDEN = "event_burden_proxy"
BASIS_EXPERIMENTAL_CENSUS = "experimental_census"
BASIS_UNCOVERED = "uncovered"

BASIS_COPY = {
    BASIS_CAPACITY: "Divided by a measured capacity base for this sector.",
    BASIS_PROXY_CAPACITY: (
        "Divided by a capacity base belonging to a DIFFERENT sector, because none exists for "
        "this one. The value is a share of that borrowed base, not of this sector's own."),
    BASIS_EVENT_BURDEN: (
        "A weighted count of concurrent facility-events against a chosen saturation constant. "
        "There is no physical capacity denominator behind it, and it says nothing about how much "
        "of the network is offline."),
    BASIS_EXPERIMENTAL_CENSUS: (
        "A bottom-up census exists but has not graduated to scoring: the published totals it "
        "would need are not like-for-like, so no defensible ratio can be formed."),
    BASIS_UNCOVERED: "No capacity base and no census. Nothing here is measured.",
}

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


def _commit_date(path):
    """When this file last changed in the repository — the honest retrieval date for our own
    curated records, whose filesystem mtime is merely when the working copy was last written."""
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", str(path)],
            cwd=str(ROOT), capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return _parse_date(r.stdout.decode("utf-8", "replace").strip())


def _evidence_dates(path, prefer_commit=False):
    """(retrieved_at, how we know, discovered release) for one source's evidence artefact.

    A manifest that states its own retrieval date is believed first. For our own curated files
    the repository commit date is the meaningful one. Otherwise the cache file's modification
    time is used and LABELLED as ours, because a fresh clone shows today for a file it never
    downloaded, and that must never be read as the publisher being current.
    """
    if not path or not path.exists():
        return None, RETRIEVAL_UNKNOWN, None
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
                return _parse_date(stated), RETRIEVAL_MANIFEST, release
    if prefer_commit:
        committed = _commit_date(path)
        if committed:
            return committed, RETRIEVAL_COMMIT, release
    mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).date()
    return mtime, RETRIEVAL_CACHE_MTIME, release


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


def _derived_release(row, evidence):
    """A release identifier the source carries in its own data rather than in a filename.

    CREA publishes monthly, so its latest reporting month IS an identifiable release — flagging
    it as "no release identifier" was an artefact of not looking inside the file.
    """
    spec = row.get("release_derivation")
    if not spec or not spec.startswith("max_column:") or not evidence or not evidence.exists():
        return None
    column = spec.split(":", 1)[1]
    try:
        values = [r.get(column) for r in read_csv(evidence) if r.get(column)]
    except (OSError, ValueError):
        return None
    return max(values) if values else None


def build_sources(as_of):
    """The structured source records the Data Quality view renders."""
    as_of_date = _parse_date(as_of) or dt.date.today()
    out = []
    for row in load_registry():
        evidence = ROOT / row["evidence_path"] if row.get("evidence_path") else None
        internal = row.get("release_expectation") == "internal"
        retrieved, basis, discovered_release = _evidence_dates(evidence, prefer_commit=internal)
        frozen = _parse_date(row.get("frozen_at"))
        release_id = (row.get("release_identifier") or discovered_release
                      or _derived_release(row, evidence))
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
                "internal_versioned_by_repo" if internal else
                "snapshot_of_a_live_source" if row.get("release_expectation") == "live" else
                "release_expected_but_absent"),
            # §4: a missing release identifier is only a finding where the publisher issues
            # releases relevant to the data actually in use. It is never a quality penalty for a
            # continuously maintained source that has no releases to miss.
            "release_gap_matters": (row.get("release_gap_matters") or "").lower() == "yes",
            "release_gap_note": row.get("release_gap_note") or None,
            "retrieval_basis_label": RETRIEVAL_LABEL[basis],
            "retrieval_is_publisher_signal": RETRIEVAL_IS_PUBLISHER_SIGNAL[basis],
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
    """Two INDEPENDENT facts per sector (addendum §1).

    `index_participation` says whether the sector is inside the headline composite.
    `methodology_basis` says what kind of measurement it rests on.

    They are orthogonal, and the previous single ladder — scored / experimental / uncovered —
    conflated them in the worst possible direction: transmission came out as "experimental",
    which a reader would fairly take to mean it is excluded from the headline. It is not. It is
    fully scored in the headline ESDI on an event-burden proxy. Both halves of that sentence
    matter, and neither can be dropped without misleading.
    """
    covered = set(snapshot.get("sectors_covered") or [])
    sectors = (explanations or {}).get("sectors") or {}
    experimental = snapshot.get("experimental_indices") or {}
    states = []
    for s in SECTORS:
        entry = sectors.get(s) or {}
        mechanism = entry.get("mechanism")
        participation = (PARTICIPATION_SCORED if s in covered
                         else PARTICIPATION_NOT_SCORED)

        if mechanism == "event_burden":
            basis = BASIS_EVENT_BURDEN
        elif s == "oil_logistics":
            # Borrows the refining capacity base; a share of someone else's denominator is not
            # the same claim as a share of your own.
            basis = BASIS_PROXY_CAPACITY
        elif s in covered:
            basis = BASIS_CAPACITY
        elif any(k.startswith(s) or s in k for k in experimental):
            basis = BASIS_EXPERIMENTAL_CENSUS
        else:
            basis = BASIS_UNCOVERED

        exp = next((v for k, v in experimental.items() if k.startswith(s) or s in k), None)
        denominator = entry.get("denominator") or {}
        states.append({
            "sector": s,
            "index_participation": participation,
            "methodology_basis": basis,
            "basis_explanation": BASIS_COPY[basis],
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
            "experimental_index": ({
                "in_headline_esdi": exp.get("in_headline_esdi"),
                "graduation_decision": exp.get("graduation_decision"),
                "graduation_reasons": exp.get("graduation_reasons") or [],
                "census_plants": exp.get("census_plants"),
            } if exp else None),
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

    # Stated against the universe where the question HAS a unit, not against every event in the
    # corpus (addendum §2). UNKNOWN is not NOT-APPLICABLE: an eleven-event substation tally
    # counted as "unknown capacity removed" would inflate a known-unknown with events for which
    # this model holds no capacity magnitude to remove.
    audit = snapshot.get("capacity_measurement_audit") or {}
    buckets = audit.get("buckets") or {}
    applicable = audit.get("applicable_events") or 0
    measured = buckets.get("measured", 0)
    if applicable and measured < applicable:
        na = buckets.get("no_modelled_capacity_dimension", 0)
        base_unknown = buckets.get("applicable_base_unknown", 0)
        items.append({
            "question": "How much capacity a given strike actually removed",
            "answer": (
                f"Not known for {applicable - measured} of the {applicable} events where the "
                f"question has a unit in this model. Open reporting almost never states it, and "
                f"nothing here fills that gap with an estimate. A further {na} event(s) struck "
                f"facilities carrying no modelled capacity magnitude, where the question has no "
                f"unit rather than an unknown answer. Of the applicable events, {base_unknown} "
                f"hit a facility whose own capacity is itself unrecorded. The index measures "
                f"capacity AT disrupted sites — exposure, not loss."),
            "basis": "capacity_measurement_audit",
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
        "capacity_measurement_audit": snapshot.get("capacity_measurement_audit"),
        "sources": sources,
        "sources_by_freshness": by_status,
        # Only the publishers that DO issue releases and were nonetheless read without one.
        # Listing every undated wiki here would bury the two entries that actually matter.
        # §4: a missing release identifier is reported only where the publisher issues releases
        # that bear on the data in use. Listing every undated source would turn a real citation
        # problem into background noise.
        "sources_without_release_identifier": [
            s["source_id"] for s in sources
            if s["citability"] == "release_expected_but_absent" and s["release_gap_matters"]],
        "release_gaps": [
            {"source_id": s["source_id"], "name": s["name"], "note": s["release_gap_note"]}
            for s in sources
            if s["citability"] == "release_expected_but_absent" and s["release_gap_matters"]],
        "citability_note": (
            "A source read from a live feed is a snapshot taken on a date, not a publication "
            "issued on one. It cannot be cited as a dated release however recently it was read."),
        "cannot_tell_you": cannot_tell_you(snapshot, explanations),
    }
