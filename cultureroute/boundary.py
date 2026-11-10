"""India boundary validation module for CultureRoute.

Validates that latitude and longitude coordinates fall within the geographical boundary of India.
Uses a verified multi-polygon point-in-polygon algorithm against official ISO 3166-1 IND geometry,
supporting exterior boundary rings and interior exclusion holes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

# Broad bounding box for India (pre-filter)
INDIA_BBOX = {
    "min_lon": 68.143,
    "max_lon": 97.396,
    "min_lat": 6.745,
    "max_lat": 37.100,
}


def is_coordinate_in_india_bbox(lat: float, lon: float) -> bool:
    """Quick bounding-box test for India geographic coordinates."""
    return (
        INDIA_BBOX["min_lat"] <= lat <= INDIA_BBOX["max_lat"] and
        INDIA_BBOX["min_lon"] <= lon <= INDIA_BBOX["max_lon"]
    )


def point_in_polygon(x: float, y: float, ring: List[List[float]]) -> bool:
    """Ray casting point-in-polygon check (x=lon, y=lat)."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    p1x, p1y = ring[0]
    for i in range(n + 1):
        p2x, p2y = ring[i % n]
        if (p1y == p2y == y) and min(p1x, p2x) <= x <= max(p1x, p2x):
            return True
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


class IndiaBoundaryValidator:
    """Validates points against canonical country boundary polygon(s) with holes support."""

    def __init__(self, geojson_path: Optional[Path] = None):
        self.geojson_path = Path(geojson_path) if geojson_path else None
        self._polygons: List[Tuple[List[List[float]], List[List[List[float]]]]] = []
        self._bbox: Optional[Tuple[float, float, float, float]] = None
        self._lat_bins: List[List[Tuple[float, float, float, float, float, float, float, int, bool]]] = [
            [] for _ in range(400)
        ]
        self._load_geojson(self.geojson_path)

    def _load_geojson(self, path: Optional[Path]) -> None:
        if not path or not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("type") == "FeatureCollection":
                features = data.get("features", [])
                geometries = [f.get("geometry", {}) for f in features if f.get("geometry")]
            elif data.get("type") == "Feature":
                geometries = [data.get("geometry", {})]
            else:
                geometries = [data]

            for geom in geometries:
                geom_type = geom.get("type")
                coords = geom.get("coordinates", [])
                if geom_type == "MultiPolygon":
                    for poly in coords:
                        if poly and len(poly) > 0:
                            ext_ring = poly[0]
                            holes = poly[1:] if len(poly) > 1 else []
                            self._polygons.append((ext_ring, holes))
                elif geom_type == "Polygon":
                    if coords and len(coords) > 0:
                        ext_ring = coords[0]
                        holes = coords[1:] if len(coords) > 1 else []
                        self._polygons.append((ext_ring, holes))

            if self._polygons:
                min_lon = min(pt[0] for ext, _ in self._polygons for pt in ext)
                max_lon = max(pt[0] for ext, _ in self._polygons for pt in ext)
                min_lat = min(pt[1] for ext, _ in self._polygons for pt in ext)
                max_lat = max(pt[1] for ext, _ in self._polygons for pt in ext)
                self._bbox = (min_lat, max_lat, min_lon, max_lon)

                # Precompute indexed y-interval bins for ray casting
                self._build_edge_index()
        except Exception:
            self._polygons = []
            self._bbox = None
            self._lat_bins = [[] for _ in range(400)]

    def _build_edge_index(self) -> None:
        self._lat_bins = [[] for _ in range(400)]
        for p_idx, (p_ext, p_holes) in enumerate(self._polygons):
            # Index exterior ring edges
            n = len(p_ext)
            for i in range(n):
                p1x, p1y = p_ext[i]
                p2x, p2y = p_ext[(i + 1) % n]
                min_y, max_y = min(p1y, p2y), max(p1y, p2y)
                edge = (p1x, p1y, p2x, p2y, min_y, max_y, max(p1x, p2x), p_idx, False)
                b_start = max(0, int(min_y * 10))
                b_end = min(399, int(max_y * 10))
                for b in range(b_start, b_end + 1):
                    self._lat_bins[b].append(edge)

            # Index hole edges
            for h_idx, hole in enumerate(p_holes):
                hn = len(hole)
                for i in range(hn):
                    p1x, p1y = hole[i]
                    p2x, p2y = hole[(i + 1) % hn]
                    min_y, max_y = min(p1y, p2y), max(p1y, p2y)
                    # Use negative ID or marker for hole
                    edge = (p1x, p1y, p2x, p2y, min_y, max_y, max(p1x, p2x), (p_idx * 1000) + h_idx, True)
                    b_start = max(0, int(min_y * 10))
                    b_end = min(399, int(max_y * 10))
                    for b in range(b_start, b_end + 1):
                        self._lat_bins[b].append(edge)

    @property
    def is_available(self) -> bool:
        return len(self._polygons) > 0

    def is_inside(self, lat: float, lon: float, strict: bool = False) -> bool:
        if not self.is_available:
            if strict:
                raise RuntimeError("Coordinate validation unavailable: boundary polygon not loaded")
            return False

        min_lat, max_lat, min_lon, max_lon = self._bbox
        if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
            return False

        bin_idx = int(lat * 10)
        if bin_idx < 0 or bin_idx >= 400:
            return False

        candidate_edges = self._lat_bins[bin_idx]
        if not candidate_edges:
            return False

        poly_inside: Dict[int, bool] = {}
        hole_inside: Dict[int, bool] = {}

        for p1x, p1y, p2x, p2y, min_y, max_y, max_x, ident, is_hole in candidate_edges:
            if min_y < lat <= max_y:
                if lon <= max_x:
                    if p1x == p2x or lon <= ((lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x):
                        if is_hole:
                            hole_inside[ident] = not hole_inside.get(ident, False)
                        else:
                            poly_inside[ident] = not poly_inside.get(ident, False)

        for p_idx, is_in in poly_inside.items():
            if is_in:
                # Check if point falls within any holes belonging to this polygon
                in_any_hole = False
                for h_key, h_in in hole_inside.items():
                    if h_in and (h_key // 1000) == p_idx:
                        in_any_hole = True
                        break
                if not in_any_hole:
                    return True

        return False
