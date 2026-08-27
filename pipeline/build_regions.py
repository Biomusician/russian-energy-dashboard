"""Build the administrative-region layer from Natural Earth.

Natural Earth 10m admin-1 is public domain, which makes it the only boundary set we
can redistribute in the repo without an attribution or share-alike obligation
propagating into the deployed site. GADM is more accurate but its licence forbids
commercial redistribution, so it is deliberately not used.

Emits two files, because they serve different masters:
  regions.json     -- metadata, joined against by every other layer
  regions.geojson  -- simplified display geometry, sized for the browser
Full-precision geometry never leaves this module; it is used in memory to build the
point-in-region index and then discarded.
"""

from pipeline import geo
from pipeline.config import PROCESSED, aoi_regions, context_units
from pipeline.util import fetch, log, read_json, write_json

NE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_10m_admin_1_states_provinces.geojson"
)

# ~1 km at these latitudes. Fine enough that borders read correctly at country and
# region zoom, coarse enough to keep the payload small.
SIMPLIFY_TOLERANCE = 0.01


def load_natural_earth():
    fetch(NE_URL, "ne_10m_admin_1.geojson", max_age_hours=24 * 30)
    return read_json(PROCESSED.parent / "raw" / "ne_10m_admin_1.geojson")


def build():
    log("regions: loading Natural Earth admin-1")
    ne = load_natural_earth()
    wanted = aoi_regions()
    specials = context_units()

    # Names Natural Earth uses for special (Crimea) geometry, so they are not mistaken
    # for an unmatched AOI region.
    special_ne_names = {n for u in specials.values() for n in u["natural_earth_names"]}

    matched = {}
    special_feats = {}
    for feat in ne["features"]:
        props = feat["properties"]
        if props.get("adm0_a3") not in ("RUS", "BLR"):
            continue
        name = props.get("name")
        if name in special_ne_names:
            special_feats[name] = feat
            continue
        if name not in wanted:
            continue
        if name in matched:
            raise RuntimeError(f"duplicate Natural Earth feature for {name!r}")
        matched[name] = feat

    missing = sorted(set(wanted) - set(matched))
    if missing:
        raise RuntimeError(
            "AOI regions absent from Natural Earth: "
            + ", ".join(missing)
            + " -- the name join key in config.RU_REGIONS/BY_REGIONS has drifted"
        )

    log(f"regions: matched {len(matched)}/{len(wanted)} AOI regions")

    meta = []
    features = []
    index_input = []

    for ne_name, feat in sorted(matched.items()):
        code, display, district, country = wanted[ne_name]
        geom = feat["geometry"]
        index_input.append((code, geom))
        meta.append(_meta_entry(code, display, ne_name, district, country, geom, esdi_included=True, special=None))
        features.append(_feature(code, display, district, country, geom, special=None))

    # Special context units (Crimea): merge the named Natural Earth features into one.
    for unit in specials.values():
        parts = [special_feats[n]["geometry"] for n in unit["natural_earth_names"] if n in special_feats]
        if not parts:
            raise RuntimeError(f"no Natural Earth geometry found for special unit {unit['code']}")
        geom = geo.merge_geometries(parts)
        index_input.append((unit["code"], geom))
        entry = _meta_entry(
            unit["code"], unit["name"], "+".join(unit["natural_earth_names"]),
            unit["district"], unit["country"], geom,
            esdi_included=unit["esdi_included"], special=unit,
        )
        meta.append(entry)
        features.append(_feature(
            unit["code"], unit["name"], unit["district"], unit["country"], geom,
            special=unit,
        ))
        log(f"regions: built special unit {unit['code']} ({unit['name']}) from "
            f"{len(parts)} Natural Earth feature(s)")

    write_json(PROCESSED / "regions.json", meta)
    write_json(PROCESSED / "regions.geojson", {"type": "FeatureCollection", "features": features})

    size_mb = (PROCESSED / "regions.geojson").stat().st_size / 1e6
    log(f"regions: wrote {len(meta)} regions, geometry {size_mb:.2f} MB")

    return geo.RegionIndex(index_input), {m["code"]: m for m in meta}


def _meta_entry(code, display, ne_name, district, country, geom, esdi_included, special):
    centre = geo.representative_point(geom)
    minx, miny, maxx, maxy = geo.bbox_of_geometry(geom)
    entry = {
        "code": code,
        "name": display,
        "natural_earth_name": ne_name,
        "district": district,
        "country": country,
        "esdi_included": esdi_included,
        "centroid": [round(centre[0], 4), round(centre[1], 4)],
        "bbox": [round(v, 4) for v in (minx, miny, maxx, maxy)],
    }
    if special:
        entry["analytic_scope"] = special["analytic_scope"]
        entry["sovereignty"] = special["sovereignty"]
        entry["de_facto_control"] = special["de_facto_control"]
        entry["status_note"] = special["note"]
    return entry


def _feature(code, display, district, country, geom, special):
    props = {
        "code": code,
        "name": display,
        "district": district,
        "country": country,
        "special": bool(special),
    }
    if special:
        props["analytic_scope"] = special["analytic_scope"]
    simple = geo.simplify_geometry(geom, SIMPLIFY_TOLERANCE)
    if simple is None:
        raise RuntimeError(f"{code} simplified to nothing at tolerance {SIMPLIFY_TOLERANCE}")
    return {
        "type": "Feature",
        "id": code,
        "properties": props,
        "geometry": geo.round_coords(simple, 3),
    }


if __name__ == "__main__":
    build()
