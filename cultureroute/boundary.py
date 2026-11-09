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
        except Exception:
            self._polygons = []
            self._bbox = None

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

        for ext_ring, holes in self._polygons:
            if point_in_polygon(lon, lat, ext_ring):
                in_hole = any(point_in_polygon(lon, lat, hole) for hole in holes)
                if not in_hole:
                    return True
        return False
