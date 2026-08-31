"""Import a Global Energy Monitor pipeline tracker (GGIT gas / GOIT oil+NGL).

    python -m pipeline.import_gem <file.geojson|file.xlsx> --tracker GGIT --release 2025-11
    python -m pipeline.import_gem --source map-data --tracker GOIT     (provisional, see below)

WHY AN IMPORTER RATHER THAN A FETCHER. GEM's citable releases are CC BY 4.0 and redistributable,
but they are delivered through a request form with no stable URL — so the authoritative path is a
human downloading a release once and dropping the file here. The importer's job is to make that
safe: a wrong export must produce a loud error, never a plausible-looking network.

TWO SOURCES, DELIBERATELY NOT EQUAL:

  release   (default)  The quarterly download. Citable, versioned, carries its own data dictionary
                       and copyright sheet, and retains `RouteAccuracy = "no route"` rows. This is
                       the baseline a provenance-backed atlas should rest on.

  map-data  (opt-in)   GEM's public `goit-ggit-data-ops` `map-data` branch. Full schema including
                       RouteAccuracy, refreshed daily, unauthenticated. BUT it is generated from
                       GEM's live backend sheet, carries NO release identifier, and drops the
                       null-geometry parent rows. Anything imported from it is stamped provisional
                       so it can never be mistaken for a citable release.

WHAT IS NEVER DONE HERE: the form is not scripted, no personal data is submitted, and the
authenticated backend sheet is not touched (GEM disabled its anonymous CSV endpoints in July 2026
and asks explicitly that no public-URL fallback be reintroduced).
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from pipeline.util import log, write_json

VENDOR = Path(__file__).resolve().parent.parent / "data" / "vendor" / "gem"

TRACKERS = ("GGIT", "GOIT")

# Columns that must exist or the file is not the tracker it claims to be. Deliberately a REQUIRED
# subset rather than the full 54/50-key set: GEM adds and renames columns between releases, and an
# importer that rejects a release for gaining a column is an importer nobody will run.
REQUIRED_COLUMNS = {
    "GGIT": ("ProjectID", "PipelineName", "Status", "Fuel", "CountriesOrAreas",
             "StartCountryOrArea", "EndCountryOrArea", "RouteAccuracy"),
    "GOIT": ("ProjectID", "PipelineName", "Status", "Fuel", "CountriesOrAreas",
             "StartCountryOrArea", "EndCountryOrArea", "RouteAccuracy"),
}

# GEM's RouteAccuracy vocabulary, lower-cased. An unrecognised value is a HARD ERROR: silently
# bucketing an unknown accuracy is exactly how "generalized" becomes "mapped".
#
# `very high (within meters)` is here because this check caught it. GEM's published QC script
# (scripts/qc_routes.py) lists five tiers; the live data carries a sixth, used on 131 GGIT and 172
# GOIT routes. The importer refused the real file on first contact rather than guessing — which is
# the entire argument for the closed vocabulary. Do not replace this with a permissive default.
ROUTE_ACCURACY_VALUES = {
    "very high (within meters)", "high", "medium", "low",
    "very low (straight line/schematic)", "no route", "",
}

# GEM RouteAccuracy -> this project's route-quality vocabulary. Conservative by construction:
# nothing below `high` may claim traced geometry, and `no route` carries no geography at all.
ROUTE_QUALITY = {
    "very high (within meters)": "gem_traced",
    "high": "gem_traced",
    "medium": "gem_generalized",
    "low": "gem_generalized",
    "very low (straight line/schematic)": "topology_only",
    "no route": "topology_only",
    "": "unresolved",
}

# GEM writes "--" for a missing numeric. That is NOT zero and NOT null-as-in-not-applicable; it is
# "unknown", which this project models as a distinct state.
SENTINELS = ("--", "", "N/A", "TBD")

MAP_DATA_URL = ("https://raw.githubusercontent.com/GlobalEnergyMonitor/"
                "goit-ggit-data-ops/map-data/{stem}_map_latest.geojson")
MAP_DATA_STEM = {"GGIT": "ggit", "GOIT": "goit"}


class ImportError_(Exception):
    """Raised for any condition that would let wrong data in."""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _clean(value):
    """GEM sentinel -> None, so 'unknown' never becomes 0."""
    if value is None:
        return None
    s = str(value).strip()
    return None if s in SENTINELS else s


def read_features(path):
    """GeoJSON FeatureCollection -> [(properties, geometry)]. xlsx is rejected with guidance."""
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        raise ImportError_(
            "This build reads the GeoJSON/GeoPackage export, not the xlsx: the xlsx no longer "
            "carries route geometry (GEM's GOIT FAQ). Re-export or download the GIS format.")
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection":
        raise ImportError_(f"{p.name}: not a GeoJSON FeatureCollection")
    return [(f.get("properties") or {}, f.get("geometry")) for f in data.get("features", [])]


def validate(features, tracker, release, provisional):
    """Every check that must pass before a single row is trusted."""
    if tracker not in TRACKERS:
        raise ImportError_(f"unknown tracker {tracker!r}; expected one of {TRACKERS}")
    if not features:
        raise ImportError_("file contains no features")
    if not provisional and not release:
        raise ImportError_(
            "a citable release import needs --release (e.g. 2025-11 for GGIT, 2026-06 for GOIT). "
            "Use --source map-data if you deliberately want the unversioned live export.")

    keys = set(features[0][0])
    missing = [c for c in REQUIRED_COLUMNS[tracker] if c not in keys]
    if missing:
        raise ImportError_(
            f"{tracker}: required columns missing: {missing}. This does not look like a "
            f"{tracker} export — check you did not swap GGIT and GOIT, or an older schema.")

    # Commodity sanity: GGIT is gas-only, GOIT is oil/NGL. Swapping the files is the single most
    # likely human error and would silently invert two whole asset classes.
    fuels = {(_clean(p.get("Fuel")) or "").lower() for p, _ in features}
    fuels.discard("")
    if tracker == "GGIT" and fuels and not fuels <= {"gas"}:
        raise ImportError_(f"GGIT should contain gas only; found Fuel values {sorted(fuels)}")
    if tracker == "GOIT" and fuels and not fuels <= {"oil", "ngl", "oil, ngl", "oil/ngl"}:
        raise ImportError_(f"GOIT should contain oil/NGL only; found Fuel values {sorted(fuels)}")

    bad = sorted({(_clean(p.get("RouteAccuracy")) or "").lower() for p, _ in features}
                 - ROUTE_ACCURACY_VALUES)
    if bad:
        raise ImportError_(
            f"unrecognised RouteAccuracy values {bad}. Refusing rather than guessing a quality "
            f"mapping — an unknown accuracy must never be bucketed as traced geometry.")
    return True


def to_records(features, tracker, release, provisional, countries=None):
    """Normalised rows, with the SOURCE-NATIVE values preserved alongside."""
    out = []
    for props, geom in features:
        allc = (_clean(props.get("CountriesOrAreas")) or "")
        if countries and not any(c.lower() in allc.lower() for c in countries):
            continue
        acc = (_clean(props.get("RouteAccuracy")) or "").lower()
        out.append({
            "gem_project_id": _clean(props.get("ProjectID")),
            "name": _clean(props.get("PipelineName")),
            "segment_name": _clean(props.get("SegmentName")),
            "commodity": "gas" if tracker == "GGIT" else "oil",
            "fuel_native": _clean(props.get("Fuel")),
            "status_native": _clean(props.get("Status")),
            "owner": _clean(props.get("Owner")),
            "parent": _clean(props.get("Parent")),
            "countries": [c.strip() for c in allc.replace(";", ",").split(",") if c.strip()],
            "start_location": _clean(props.get("StartLocation")),
            "start_country": _clean(props.get("StartCountryOrArea")),
            "end_location": _clean(props.get("EndLocation")),
            "end_country": _clean(props.get("EndCountryOrArea")),
            # Length/capacity keep their units; nothing is converted here.
            "length_km_known": _clean(props.get("LengthKnownKm") or props.get("LengthKnown")),
            "capacity": _clean(props.get("Capacity")),
            "capacity_units": _clean(props.get("CapacityUnits")),
            # Source-native quality preserved next to the normalised mapping (addendum §7).
            "route_accuracy_native": _clean(props.get("RouteAccuracy")),
            "route_type_native": _clean(props.get("RouteType")),
            "route_quality": ROUTE_QUALITY.get(acc, "unresolved"),
            "has_geometry": bool(geom and geom.get("coordinates")),
            "tracker": tracker,
            "release": release if not provisional else None,
            "provisional": provisional,
        })
    return out


def manifest_entry(path, tracker, release, provisional, n_features, n_kept):
    citation = (f"Global Energy Monitor, "
                f"{'Global Gas Infrastructure Tracker' if tracker == 'GGIT' else 'Global Oil Infrastructure Tracker'}"
                f"{', ' + release + ' release' if release else ', live backend export (no release identifier)'}.")
    return {
        "tracker": tracker,
        "release": release,
        "provisional": provisional,
        "source_file": Path(path).name if path else MAP_DATA_URL.format(stem=MAP_DATA_STEM[tracker]),
        "sha256": sha256(path) if path else None,
        "features_in_file": n_features,
        "features_kept": n_kept,
        "licence": "CC-BY-4.0",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "citation": citation,
        "modified": "Filtered to the monitored area; geometry simplified for display.",
        "provisional_note": (
            "Imported from GEM's public map-data branch, which is generated from the live backend "
            "sheet: it has NO release identifier, changes daily, and omits null-geometry parent "
            "rows. Not a citable release." if provisional else None),
    }


def run(path, tracker, release=None, provisional=False, countries=None, dry_run=False):
    features = read_features(path)
    validate(features, tracker, release, provisional)
    records = to_records(features, tracker, release, provisional, countries)
    man = manifest_entry(path, tracker, release, provisional, len(features), len(records))

    log(f"gem-import: {tracker} {release or 'PROVISIONAL live export'}")
    log(f"  features in file : {len(features)}")
    log(f"  kept after filter: {len(records)}")
    import collections
    log(f"  route_quality    : {dict(collections.Counter(r['route_quality'] for r in records))}")
    log(f"  with geometry    : {sum(1 for r in records if r['has_geometry'])}")
    if dry_run:
        log("  DRY RUN — nothing written")
        return records, man

    VENDOR.mkdir(parents=True, exist_ok=True)
    stem = f"gem_{tracker.lower()}"
    write_json(VENDOR / f"{stem}_records.json", records)
    manifests = {}
    mpath = VENDOR / "MANIFEST.json"
    if mpath.exists():
        manifests = json.loads(mpath.read_text(encoding="utf-8"))
    manifests[tracker] = man
    write_json(mpath, manifests)
    log(f"  wrote {VENDOR / (stem + '_records.json')}")
    return records, man


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", nargs="?", help="GEM GeoJSON export (omit with --source map-data)")
    ap.add_argument("--tracker", required=True, choices=TRACKERS)
    ap.add_argument("--release", help="release label, e.g. 2025-11 (GGIT) or 2026-06 (GOIT)")
    ap.add_argument("--source", choices=("release", "map-data"), default="release")
    ap.add_argument("--countries", nargs="*", help="filter to these country names")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    provisional = args.source == "map-data"
    if provisional and not args.file:
        ap.error("--source map-data still needs a downloaded copy of "
                 f"{MAP_DATA_URL.format(stem=MAP_DATA_STEM[args.tracker])} passed as `file`; "
                 "this importer does not fetch, so the input is always auditable.")
    try:
        run(args.file, args.tracker, args.release, provisional, args.countries, args.dry_run)
    except ImportError_ as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
