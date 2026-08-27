"""Build static context geography: surrounding countries, borders and the sea.

The analytic map should read as a place, not a Russia-shaped surface floating on black.
This emits three small, simplified, public-domain GeoJSON files that the frontend draws
underneath the analytic regions:

  context_land.geojson    -- neighbouring country fills (muted, no choropleth)
  context_borders.geojson -- their outlines
  ocean.geojson           -- sea fill, so the Black Sea reads as water

Source is Natural Earth 50m (public domain). 50m, not 10m: context countries are
scenery, and 10m would multiply the payload for detail no one reads at this zoom. These
countries are DISPLAY ONLY -- no infrastructure is ingested and nothing here is scored.
The map does not draw any energy symbol or event marker on them.

Labels are NOT baked into these files. The frontend renders country and sea labels as
HTML overlays positioned with map.project(), which keeps the map free of any glyph
endpoint and therefore free of external network dependencies.
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

# Neighbours and context states the brief asks to show, by Natural Earth adm0_a3. These
# are context geography only; being listed here grants display, never analytic scope.
CONTEXT_COUNTRIES = {
    "UKR": "Ukraine", "ROU": "Romania", "MDA": "Moldova", "POL": "Poland",
    "LTU": "Lithuania", "LVA": "Latvia", "EST": "Estonia", "FIN": "Finland",
    "NOR": "Norway", "GEO": "Georgia", "KAZ": "Kazakhstan", "TUR": "Turkey",
    "CHN": "China", "MNG": "Mongolia", "AZE": "Azerbaijan",
    "SWE": "Sweden", "BGR": "Bulgaria", "SVK": "Slovakia", "HUN": "Hungary",
    "ARM": "Armenia", "KGZ": "Kyrgyzstan", "UZB": "Uzbekistan", "TKM": "Turkmenistan",
    "DEU": "Germany", "CZE": "Czechia", "BLR": None,  # Belarus drawn as analytic, skip
}

# Clip everything to a generous frame around the AOI so we never ship, say, all of
# China or Canada. west, south, east, north.
CLIP = (5.0, 34.0, 130.0, 82.0)

LAND_TOLERANCE = 0.05   # ~5 km; scenery, simplify hard
OCEAN_TOLERANCE = 0.06


def _clip_ring(ring):
    """Keep a ring only if any vertex falls inside the frame; drop far-away parts.

    A cheap bbox filter, not a true clip. It discards a country's distant islands and
    overseas parts (French Guiana, Norwegian Arctic islands) without pulling in a
    clipping library. Rings that straddle the frame are kept whole and simplified.
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


def build():
    log("context: loading Natural Earth 50m admin-0 + ocean")
    fetch(ADMIN0_URL, "ne_50m_admin_0.geojson", max_age_hours=24 * 30)
    fetch(OCEAN_URL, "ne_50m_ocean.geojson", max_age_hours=24 * 30)
    admin0 = read_json(RAW / "ne_50m_admin_0.geojson")
    ocean = read_json(RAW / "ne_50m_ocean.geojson")

    land_features = []
    border_features = []
    for feat in admin0["features"]:
        props = feat["properties"]
        iso = props.get("ADM0_A3") or props.get("adm0_a3")
        if iso not in CONTEXT_COUNTRIES or CONTEXT_COUNTRIES[iso] is None:
            continue
        geom = _clip_geometry(feat["geometry"], LAND_TOLERANCE)
        if geom is None:
            continue
        name = CONTEXT_COUNTRIES[iso]
        centre = geo.representative_point(geom)
        land_features.append({
            "type": "Feature",
            "properties": {"iso": iso, "name": name,
                           "label_lon": round(centre[0], 3), "label_lat": round(centre[1], 3)},
            "geometry": geo.round_coords(geom, 2),
        })
        border_features.append({
            "type": "Feature",
            "properties": {"iso": iso},
            "geometry": geo.round_coords(geom, 2),
        })

    ocean_features = []
    for feat in ocean["features"]:
        geom = _clip_geometry(feat["geometry"], OCEAN_TOLERANCE)
        if geom is not None:
            ocean_features.append({
                "type": "Feature", "properties": {}, "geometry": geo.round_coords(geom, 2),
            })

    write_json(PROCESSED / "context_land.geojson", {"type": "FeatureCollection", "features": land_features})
    write_json(PROCESSED / "context_borders.geojson", {"type": "FeatureCollection", "features": border_features})
    write_json(PROCESSED / "ocean.geojson", {"type": "FeatureCollection", "features": ocean_features})

    total = sum((PROCESSED / f).stat().st_size for f in
                ("context_land.geojson", "context_borders.geojson", "ocean.geojson")) / 1e6
    log(f"context: {len(land_features)} countries, {len(ocean_features)} ocean parts, {total:.2f} MB")


if __name__ == "__main__":
    build()
