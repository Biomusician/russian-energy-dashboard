"""Geometry helpers.

Hand-rolled rather than pulled from shapely/geopandas. The pipeline only needs
point-in-polygon, bounding boxes, area-weighted centroids and line simplification,
all of which are short and dependency-free. Keeping the ETL stdlib-only means the
GitHub Action needs no build toolchain and cannot break on a wheel that stops
publishing for Python 3.13.

All coordinates are (lon, lat) degrees, matching GeoJSON order.
"""

import math


def bbox_of_ring(ring):
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return (min(lons), min(lats), max(lons), max(lats))


def bbox_of_geometry(geom):
    """Bounding box of a GeoJSON Polygon or MultiPolygon."""
    minx = miny = math.inf
    maxx = maxy = -math.inf
    for poly in _polygons(geom):
        x0, y0, x1, y1 = bbox_of_ring(poly[0])
        minx, miny = min(minx, x0), min(miny, y0)
        maxx, maxy = max(maxx, x1), max(maxy, y1)
    return (minx, miny, maxx, maxy)


def _polygons(geom):
    """Yield each polygon (list of rings) from a Polygon or MultiPolygon."""
    t = geom["type"]
    if t == "Polygon":
        yield geom["coordinates"]
    elif t == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield poly
    else:
        raise ValueError("unsupported geometry type: " + t)


def point_in_ring(lon, lat, ring):
    """Standard ray-casting test. Ring is a closed list of [lon, lat]."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        # Does the edge straddle the horizontal ray at `lat`?
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_geometry(lon, lat, geom):
    """True if the point is inside the polygon and not inside any of its holes."""
    for poly in _polygons(geom):
        if not poly:
            continue
        if point_in_ring(lon, lat, poly[0]):
            in_hole = any(point_in_ring(lon, lat, hole) for hole in poly[1:])
            if not in_hole:
                return True
    return False


class RegionIndex:
    """Assigns points to regions.

    A flat scan over 69 regions with multi-megabyte polygons is too slow for tens of
    thousands of points, so each region gets a bounding-box prefilter. That reduces
    the expensive ray-casting to the handful of regions whose box actually contains
    the point.
    """

    def __init__(self, regions):
        # regions: list of (code, geometry)
        self.entries = [(code, bbox_of_geometry(g), g) for code, g in regions]

    def find(self, lon, lat):
        """Return the region code containing the point, or None."""
        for code, (x0, y0, x1, y1), geom in self.entries:
            if x0 <= lon <= x1 and y0 <= lat <= y1:
                if point_in_geometry(lon, lat, geom):
                    return code
        return None


def ring_area_and_centroid(ring):
    """Signed planar area and centroid of a ring, via the shoelace formula.

    Degrees are treated as a flat plane. That is wrong for absolute area but fine
    here: the result is only used to pick the visual centre of a region for label
    and marker placement, and to choose the largest part of a multipolygon.
    """
    a = 0.0
    cx = 0.0
    cy = 0.0
    n = len(ring)
    for i in range(n - 1):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[i + 1][0], ring[i + 1][1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if abs(a) < 1e-12:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return 0.0, (sum(xs) / len(xs), sum(ys) / len(ys))
    return a, (cx / (6 * a), cy / (6 * a))


def representative_point(geom):
    """A point to hang a region's label on: the centroid of its largest polygon.

    Uses the largest part rather than the whole multipolygon so that a region with
    distant small islands does not get a label floating in open water.
    """
    best_area = -1.0
    best_centre = None
    for poly in _polygons(geom):
        if not poly:
            continue
        area, centre = ring_area_and_centroid(poly[0])
        area = abs(area)
        if area > best_area:
            best_area, best_centre = area, centre
    return best_centre


def _perpendicular_distance(pt, start, end):
    x, y = pt[0], pt[1]
    x0, y0 = start[0], start[1]
    x1, y1 = end[0], end[1]
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return math.hypot(x - x0, y - y0)
    return abs(dy * x - dx * y + x1 * y0 - y1 * x0) / math.hypot(dx, dy)


def simplify_ring(ring, tolerance):
    """Douglas-Peucker. Returns a ring with at least 4 points, still closed."""
    if len(ring) <= 4:
        return ring
    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        max_dist = -1.0
        index = first
        for i in range(first + 1, last):
            d = _perpendicular_distance(ring[i], ring[first], ring[last])
            if d > max_dist:
                max_dist, index = d, i
        if max_dist > tolerance:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    out = [p for p, k in zip(ring, keep) if k]
    if len(out) < 4:
        return ring
    if out[0] != out[-1]:
        out.append(out[0])
    return out


def simplify_geometry(geom, tolerance, min_ring_points=6):
    """Simplify a Polygon/MultiPolygon for display.

    Rings that collapse below `min_ring_points` after simplification are dropped
    entirely -- they are slivers and islands too small to see at dashboard zoom.
    A polygon whose outer ring is dropped is dropped with it.
    """
    out_polys = []
    for poly in _polygons(geom):
        rings = []
        for i, ring in enumerate(poly):
            s = simplify_ring(ring, tolerance)
            if len(s) >= min_ring_points:
                rings.append(s)
            elif i == 0:
                rings = []
                break
        if rings:
            out_polys.append(rings)
    if not out_polys:
        return None
    if len(out_polys) == 1:
        return {"type": "Polygon", "coordinates": out_polys[0]}
    return {"type": "MultiPolygon", "coordinates": out_polys}


def round_coords(geom, ndigits=3):
    """Round coordinates to shrink the emitted JSON.

    3 decimal places is about 100 m at these latitudes -- far finer than an
    admin-region choropleth can show, and coarse enough to halve the file size.
    """
    def r(coords):
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], ndigits), round(coords[1], ndigits)]
        return [r(c) for c in coords]

    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}
