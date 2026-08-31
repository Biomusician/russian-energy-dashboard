"""Build static context geography: surrounding countries, borders, the sea and rivers.

The analytic map should read as a place, not a Russia-shaped surface floating on black.
This emits small, simplified, public-domain GeoJSON files that the frontend draws
underneath the analytic regions:

  context_land.geojson    -- surrounding country fills (muted, no choropleth)
  context_borders.geojson -- their outlines
  ocean.geojson           -- sea fill, so the Black Sea reads as water
  rivers.geojson          -- major river centrelines (geographic context, never scored)

Source is Natural Earth 50m (public domain). 50m, not 10m: context geography is scenery,
and 10m would multiply the payload for detail no one reads at this zoom. Everything here
is DISPLAY ONLY -- no infrastructure is ingested and nothing is scored. The map draws no
energy symbol or event marker on any of it.

Iteration 5 broadened the country set: instead of a hand-picked list, EVERY country whose
geometry falls inside the frame is drawn, so the Russia-Europe network view shows a real
world, not a curated subset (§9). Two deliberate exclusions: Russia and Belarus are drawn
as ANALYTIC regions elsewhere, so they are not redrawn as context; and because Natural
Earth's 50m admin-0 files Crimea inside the Russian polygon, excluding Russia here means
Crimea is never painted as ordinary Russian context -- it is drawn only as its own
separately-identified occupied unit in the regions layer (§10).

Label priority is DATA-DRIVEN, not hardcoded in the frontend: each country carries a
`label_min_zoom` derived from Natural Earth's LABELRANK, and each river a `reveal_zoom`
from its scalerank, so the frontend reveals major features first and smaller ones on zoom
without a per-feature list in the code. Labels themselves are HTML overlays positioned
with map.project(), which keeps the map free of any glyph endpoint (no external requests).
"""

from pipeline import geo
from pipeline.config import PROCESSED, RAW
from pipeline.util import fetch, log, read_json, write_json

ADMIN0_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_50m_admin_0_countries.geojson"
)
OCEAN_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_50m_ocean.geojson"
)
RIVERS_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_50m_rivers_lake_centerlines.geojson"
)

# Countries NOT drawn as context. Russia and Belarus are analytic regions (drawn with the
# choropleth). KAS is Natural Earth's "Siachen Glacier" feature -- a disputed glacier, not
# a country, and not worth a label. Everything else inside the frame is context geography.
EXCLUDE_ISO = {"RUS", "BLR", "KAS"}

# Natural Earth LABELRANK (2 = major state ... 6 = micro) -> the map zoom at which a
# country's label may appear. Major states show at continental scale; smaller ones reveal
# as you zoom in. The frontend also de-overlaps greedily, so this is a floor, not a
# guarantee. Data-driven priority: this replaces a per-country list in the frontend.
LABELRANK_MINZOOM = {1: 0.0, 2: 0.0, 3: 2.3, 4: 3.2, 5: 3.9, 6: 4.6}
DEFAULT_LABEL_MINZOOM = 3.4

# River scalerank (1 = largest system ... 6 = minor) -> reveal zoom for the line, and a
# label reveal for the named major ones. Rank-6 rivers are dropped: minor tributaries add
# payload and clutter without adding orientation at this scale.
RIVER_REVEAL = {1: 0.0, 2: 2.6, 3: 3.4, 4: 4.2, 5: 5.0}
RIVER_MAX_SCALERANK = 5
RIVER_LABEL_MAX_SCALERANK = 3   # the biggest, named systems get a label anchor
RIVER_LABEL_SEP = 4.0            # min degrees between two river labels (geometric de-dup)
RIVER_LABEL_MIN_LAT = 43.0       # only label rivers in the AOI latitude band (drops
                                 # Middle-East / China-interior rivers at the frame edge)

# Clip everything to a Eurasian context frame. Iteration 5 widened this from the old
# 5-130E box to a real Russia-Europe extent (Atlantic Europe through the Russian Far East),
# so the network view shows where the export system actually connects (§11/§27). Russia and
# Belarus are still excluded from the country set (they are analytic); this only governs how
# far the surrounding context geography and rivers reach. west, south, east, north.
CLIP = (-12.0, 34.0, 170.0, 82.0)

LAND_TOLERANCE = 0.05    # ~5 km; scenery, simplify hard
OCEAN_TOLERANCE = 0.06
RIVER_TOLERANCE = 0.03


def _clip_ring(ring):
    """Keep a ring only if any vertex falls inside the frame; drop far-away parts.

    A cheap bbox filter, not a true clip. It discards a country's distant islands and
    overseas parts without pulling in a clipping library. Rings that straddle the frame
    are kept whole and simplified.
    """
    w, s, e, n = CLIP
    return any(w <= x <= e and s <= y <= n for x, y in ring)


def _clip_geometry(geom, tolerance):
    out = []
    for poly in geo._polygons(geom):
        if not poly or not _clip_ring(poly[0]):
            continue
        rings = []
        for i, ring in enumerate(poly):
            s = geo.simplify_ring(ring, tolerance)
            if len(s) >= 5:
                rings.append(s)
            elif i == 0:
                rings = []
                break
        if rings:
            out.append(rings)
    if not out:
        return None
    return {"type": "MultiPolygon", "coordinates": out}


def _line_parts(geom):
    """Yield each coordinate list of a LineString / MultiLineString."""
    if geom["type"] == "LineString":
        yield geom["coordinates"]
    elif geom["type"] == "MultiLineString":
        yield from geom["coordinates"]


def _simplify_line(coords, tolerance):
    """Douglas-Peucker for an OPEN polyline (a river is not a ring). Delegates to
    geo.simplify_line so the corrected point-to-SEGMENT metric is used here too."""
    return geo.simplify_line(coords, tolerance)


def _clip_line(geom, tolerance):
    """Keep the parts of a river that fall in the frame, simplified. Returns a
    LineString / MultiLineString geometry, or None if nothing survives."""
    parts = []
    for coords in _line_parts(geom):
        if not _clip_ring(coords):   # any vertex in-frame
            continue
        s = _simplify_line(coords, tolerance)
        if len(s) >= 2:
            parts.append(s)
    if not parts:
        return None
    if len(parts) == 1:
        return {"type": "LineString", "coordinates": parts[0]}
    return {"type": "MultiLineString", "coordinates": parts}


def _line_length(geom):
    """Total planar length of a line geometry, in degrees (good enough for ranking)."""
    total = 0.0
    for coords in _line_parts(geom):
        total += sum(
            ((coords[i + 1][0] - coords[i][0]) ** 2 + (coords[i + 1][1] - coords[i][1]) ** 2) ** 0.5
            for i in range(len(coords) - 1)
        )
    return total


def _line_label_anchor(geom):
    """A representative point for a river label: the midpoint vertex of its longest part.
    Placing text on a real vertex keeps the label on the line without a glyph endpoint."""
    longest, best_len = None, -1.0
    for coords in _line_parts(geom):
        length = sum(
            ((coords[i + 1][0] - coords[i][0]) ** 2 + (coords[i + 1][1] - coords[i][1]) ** 2) ** 0.5
            for i in range(len(coords) - 1)
        )
        if length > best_len:
            best_len, longest = length, coords
    if not longest:
        return None
    return longest[len(longest) // 2]


def _build_countries(admin0):
    land_features, border_features = [], []
    for feat in admin0["features"]:
        props = feat["properties"]
        iso = props.get("ADM0_A3") or props.get("adm0_a3")
        if not iso or iso in EXCLUDE_ISO:
            continue
        geom = _clip_geometry(feat["geometry"], LAND_TOLERANCE)
        if geom is None:
            continue
        name = props.get("NAME") or props.get("name") or iso
        labelrank = props.get("LABELRANK")
        label_min_zoom = LABELRANK_MINZOOM.get(labelrank, DEFAULT_LABEL_MINZOOM)
        centre = geo.representative_point(geom)
        land_features.append({
            "type": "Feature",
            "properties": {
                "iso": iso, "name": name,
                "labelrank": labelrank,
                "label_min_zoom": label_min_zoom,
                "label_lon": round(centre[0], 3), "label_lat": round(centre[1], 3),
            },
            "geometry": geo.round_coords(geom, 2),
        })
        border_features.append({
            "type": "Feature",
            "properties": {"iso": iso},
            "geometry": geo.round_coords(geom, 2),
        })
    return land_features, border_features


def _build_rivers(rivers):
    # Prefer the English name so labels read Danube / Irtysh / Euphrates, not Donau / Ertis
    # / Al Furat -- Natural Earth carries both, per segment.
    raw = []
    for feat in rivers["features"]:
        props = feat["properties"]
        sr = props.get("scalerank")
        if sr is None or sr > RIVER_MAX_SCALERANK:
            continue
        geom = _clip_line(feat["geometry"], RIVER_TOLERANCE)
        if geom is None:
            continue
        name = props.get("name_en") or props.get("name")
        raw.append((name, sr, geom))

    # Natural Earth splits one river into many segments and names them inconsistently across
    # languages (the Euphrates appears as Euphrates / Al Furat / Firat even in name_en). To
    # avoid a name-soup we label only the LARGEST systems (scalerank <= label max), then
    # de-duplicate two ways: by name (keep the longest segment of each), then geometrically
    # (drop any remaining label whose anchor is within RIVER_LABEL_SEP of one already placed,
    # which collapses cross-language variants and delta distributaries). No hardcoded river
    # list -- the emphasis comes entirely from Natural Earth's scalerank (§8).
    longest_of_name = {}
    for i, (name, sr, geom) in enumerate(raw):
        if not name or sr > RIVER_LABEL_MAX_SCALERANK:
            continue
        anchor = _line_label_anchor(geom)
        if anchor is None or anchor[1] < RIVER_LABEL_MIN_LAT:
            continue
        length = _line_length(geom)
        if name not in longest_of_name or length > longest_of_name[name][0]:
            longest_of_name[name] = (length, sr, i, anchor)
    cands = sorted((sr, -length, i, anchor)
                   for length, sr, i, anchor in longest_of_name.values() if anchor)
    placed, label_anchor = [], {}
    for sr, _neglen, i, anchor in cands:
        if all(max(abs(anchor[0] - a[0]), abs(anchor[1] - a[1])) > RIVER_LABEL_SEP for a in placed):
            placed.append(anchor)
            label_anchor[i] = anchor

    features = []
    for i, (name, sr, geom) in enumerate(raw):
        out = {"scalerank": sr, "reveal_zoom": RIVER_REVEAL.get(sr, 4.5)}
        if name:
            out["name"] = name
        if i in label_anchor:
            ax, ay = label_anchor[i]
            out["label_name"] = name
            out["label_lon"] = round(ax, 3)
            out["label_lat"] = round(ay, 3)
            out["label_zoom"] = out["reveal_zoom"] + 1.0
        features.append({
            "type": "Feature", "properties": out,
            "geometry": geo.round_coords(geom, 2),
        })
    return features


def build():
    log("context: loading Natural Earth 50m admin-0, ocean and rivers")
    fetch(ADMIN0_URL, "ne_50m_admin_0.geojson", max_age_hours=24 * 30)
    fetch(OCEAN_URL, "ne_50m_ocean.geojson", max_age_hours=24 * 30)
    fetch(RIVERS_URL, "ne_50m_rivers.geojson", max_age_hours=24 * 30)
    admin0 = read_json(RAW / "ne_50m_admin_0.geojson")
    ocean = read_json(RAW / "ne_50m_ocean.geojson")
    rivers = read_json(RAW / "ne_50m_rivers.geojson")

    land_features, border_features = _build_countries(admin0)

    ocean_features = []
    for feat in ocean["features"]:
        geom = _clip_geometry(feat["geometry"], OCEAN_TOLERANCE)
        if geom is not None:
            ocean_features.append({
                "type": "Feature", "properties": {}, "geometry": geo.round_coords(geom, 2),
            })

    river_features = _build_rivers(rivers)

    write_json(PROCESSED / "context_land.geojson", {"type": "FeatureCollection", "features": land_features})
    write_json(PROCESSED / "context_borders.geojson", {"type": "FeatureCollection", "features": border_features})
    write_json(PROCESSED / "ocean.geojson", {"type": "FeatureCollection", "features": ocean_features})
    write_json(PROCESSED / "rivers.geojson", {"type": "FeatureCollection", "features": river_features})

    total = sum((PROCESSED / f).stat().st_size for f in
                ("context_land.geojson", "context_borders.geojson", "ocean.geojson", "rivers.geojson")) / 1e6
    labelled_rivers = sum(1 for f in river_features if "label_name" in f["properties"])
    log(f"context: {len(land_features)} countries, {len(ocean_features)} ocean parts, "
        f"{len(river_features)} rivers ({labelled_rivers} labelled), {total:.2f} MB")


if __name__ == "__main__":
    build()
