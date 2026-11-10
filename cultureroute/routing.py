"""Directed Road and Walking Leg Routing Engine for CultureRoute (Phase 8).

Key Features & Architectural Discipline:
1. Genuine Directed Routing:
   - Queries an explicitly configured OSRM routing provider; there is no public default.
   - Never commits secrets; configurable via environment variables (`CULTUREROUTE_OSRM_URL`, `CULTUREROUTE_ROUTING_TIMEOUT`).
   - If provider is unreachable, returns explicit `is_available=False` with `failure_reason` explaining provider error.
   - NO fabricated legs: straight-line distance multiplication / synthetic bias is strictly disabled for production traveler routes.
2. Independent Directed Leg Persistence:
   - Stored in dedicated SQLite database (`data/real_routes.db`), separate from `real_catalog.db`.
   - Caches A -> B and B -> A independently with profile, distance, duration, exact polyline geometry, calculation timestamp, and provider metadata.
   - Cache entries include `data_version` and timestamp for staleness checks.
3. Realistic Mode Limits & Safety Constraints:
   - Walking is disabled until a separate pedestrian graph is configured and verified.
   - Coordinate validation: Rejects coordinates outside valid ranges (-90..90, -180..180).
   - Identity leg: (A -> A) returns 0 distance, 0 duration, available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple
import math
import requests

from cultureroute.catalog import haversine_distance_km

DEFAULT_ROUTES_DB = Path(__file__).resolve().parent.parent / "data" / "real_routes.db"

# Routing is opt-in. A pedestrian route requires a separately configured foot graph.
DEFAULT_OSRM_URL = os.environ.get("CULTUREROUTE_OSRM_DRIVING_URL") or os.environ.get("CULTUREROUTE_OSRM_URL")
DEFAULT_ROUTING_TIMEOUT = float(os.environ.get("CULTUREROUTE_ROUTING_TIMEOUT", "4.0"))


def configured_backend(mode: "TransportMode") -> Optional[str]:
    if mode == TransportMode.WALKING and os.environ.get("CULTUREROUTE_WALKING_PROFILE_VERIFIED") != "1":
        return None
    return (os.environ.get("CULTUREROUTE_OSRM_WALKING_URL") if mode == TransportMode.WALKING
            else os.environ.get("CULTUREROUTE_OSRM_DRIVING_URL") or os.environ.get("CULTUREROUTE_OSRM_URL"))


class TransportMode(str, Enum):
    DRIVING = "DRIVING"
    WALKING = "WALKING"


MAX_WALKING_DISTANCE_KM = 25.0


@dataclass(frozen=True)
class DirectedRouteLeg:
    origin_id: str
    destination_id: str
    mode: TransportMode
    distance_meters: float
    duration_seconds: float
    distance_km: float
    duration_minutes: float
    is_available: bool
    failure_reason: Optional[str] = None
    polyline_points: List[Tuple[float, float]] = field(default_factory=list)
    source_name: str = "OSRM Routing Engine (OpenStreetMap)"
    source_version: str = "v5.27.1"
    computed_at: str = ""
    provider_url: str = ""
    data_version: str = "unreported"
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lon: Optional[float] = None
    requested_at: Optional[str] = None
    responded_at: Optional[str] = None

    def __post_init__(self):
        if not self.computed_at:
            object.__setattr__(self, "computed_at", datetime.now(timezone.utc).isoformat())


class RouteLegStore:
    """Manages cached real-world directed routing legs independently from catalog rebuilds."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = DEFAULT_ROUTES_DB
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS real_route_legs (
                    origin_id TEXT NOT NULL,
                    destination_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    distance_meters REAL NOT NULL,
                    duration_seconds REAL NOT NULL,
                    distance_km REAL NOT NULL,
                    duration_minutes REAL NOT NULL,
                    is_available INTEGER NOT NULL,
                    failure_reason TEXT,
                    geometry_json TEXT,
                    source_name TEXT NOT NULL,
                    source_version TEXT NOT NULL,
                    computed_at TEXT NOT NULL,
                    provider_url TEXT,
                    data_version TEXT,
                    origin_lat REAL,
                    origin_lon REAL,
                    destination_lat REAL,
                    destination_lon REAL,
                    requested_at TEXT,
                    responded_at TEXT,
                    PRIMARY KEY (origin_id, destination_id, mode)
                );
                CREATE INDEX IF NOT EXISTS idx_legs_orig_dest ON real_route_legs(origin_id, destination_id);
            """)
            columns = {r[1] for r in conn.execute("PRAGMA table_info(real_route_legs)")}
            for column, kind in (("provider_url", "TEXT"), ("data_version", "TEXT"),
                                 ("origin_lat", "REAL"), ("origin_lon", "REAL"),
                                 ("destination_lat", "REAL"), ("destination_lon", "REAL"),
                                 ("requested_at", "TEXT"), ("responded_at", "TEXT")):
                if column not in columns:
                    conn.execute(f"ALTER TABLE real_route_legs ADD COLUMN {column} {kind}")

    def get_cached_leg(self, origin_id: str, destination_id: str, mode: TransportMode,
                       origin: Optional[Tuple[float, float]] = None,
                       destination: Optional[Tuple[float, float]] = None) -> Optional[DirectedRouteLeg]:
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM real_route_legs
                WHERE origin_id = ? AND destination_id = ? AND mode = ?
            """, (origin_id, destination_id, mode.value)).fetchone()

            if not row:
                return None

            try:
                geom = json.loads(row["geometry_json"]) if row["geometry_json"] else []
            except (ValueError, TypeError):
                return None
            # Legacy two-endpoint/hand-entered rows are not a routable geometry.
            if (len(geom) < 3 or not all(len(pt) == 2 and all(isinstance(v, (int, float)) and
                    math.isfinite(v) for v in pt) and -90 <= pt[0] <= 90 and -180 <= pt[1] <= 180
                    for pt in geom) or row["distance_meters"] <= 0 or row["duration_seconds"] <= 0 or
                    not row["source_name"].startswith("OSRM Directed Routing (") or
                    not row["provider_url"] or not row["data_version"] or not row["is_available"] or
                    not row["requested_at"] or not row["responded_at"]):
                return None
            try:
                checked = datetime.fromisoformat(row["computed_at"])
                if checked.tzinfo is None or (datetime.now(timezone.utc) - checked).days > 30:
                    return None
            except ValueError:
                return None
            if origin and haversine_distance_km(*origin, *geom[0]) > 2:
                return None
            if destination and haversine_distance_km(*destination, *geom[-1]) > 2:
                return None
            if origin and (row["origin_lat"] is None or
                           haversine_distance_km(*origin, row["origin_lat"], row["origin_lon"]) > 0.2):
                return None
            if destination and (row["destination_lat"] is None or
                                haversine_distance_km(*destination, row["destination_lat"], row["destination_lon"]) > 0.2):
                return None
            expected_version = os.environ.get("CULTUREROUTE_ROUTING_DATA_VERSION")
            if expected_version and row["data_version"] != expected_version:
                return None
            return DirectedRouteLeg(
                origin_id=row["origin_id"],
                destination_id=row["destination_id"],
                mode=TransportMode(row["mode"]),
                distance_meters=float(row["distance_meters"]),
                duration_seconds=float(row["duration_seconds"]),
                distance_km=float(row["distance_km"]),
                duration_minutes=float(row["duration_minutes"]),
                is_available=bool(row["is_available"]),
                failure_reason=row["failure_reason"],
                polyline_points=[(pt[0], pt[1]) for pt in geom],
                source_name=row["source_name"],
                source_version=row["source_version"],
                computed_at=row["computed_at"],
                provider_url=row["provider_url"], data_version=row["data_version"],
                origin_lat=row["origin_lat"], origin_lon=row["origin_lon"],
                destination_lat=row["destination_lat"], destination_lon=row["destination_lon"],
                requested_at=row["requested_at"], responded_at=row["responded_at"]
            )

    def insert_leg(self, leg: DirectedRouteLeg) -> None:
        if (not leg.is_available or len(leg.polyline_points) < 3 or
                not leg.source_name.startswith("OSRM Directed Routing (") or
                not leg.provider_url or leg.origin_lat is None or leg.destination_lat is None or
                not leg.requested_at or not leg.responded_at):
            raise ValueError("Only validated provider routes with actual geometry may be cached")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO real_route_legs (
                    origin_id, destination_id, mode, distance_meters, duration_seconds,
                    distance_km, duration_minutes, is_available, failure_reason,
                    geometry_json, source_name, source_version, computed_at,
                    provider_url, data_version, origin_lat, origin_lon, destination_lat, destination_lon,
                    requested_at, responded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                leg.origin_id,
                leg.destination_id,
                leg.mode.value,
                leg.distance_meters,
                leg.duration_seconds,
                leg.distance_km,
                leg.duration_minutes,
                1 if leg.is_available else 0,
                leg.failure_reason,
                json.dumps(leg.polyline_points),
                leg.source_name,
                leg.source_version,
                leg.computed_at, leg.provider_url, leg.data_version,
                leg.origin_lat, leg.origin_lon, leg.destination_lat, leg.destination_lon,
                leg.requested_at, leg.responded_at
            ))


def compute_directed_leg(
    origin_id: str,
    origin_lat: float,
    origin_lon: float,
    destination_id: str,
    destination_lat: float,
    destination_lon: float,
    mode: TransportMode,
    store: Optional[RouteLegStore] = None,
    allow_network: bool = True,
    provider_url: Optional[str] = None
) -> DirectedRouteLeg:
    """Compute genuine directed road or walking leg between two validated real coordinates.

    Invariants:
    - Never fabricates fake legs: if routing provider fails or cannot reach destination,
      explicitly returns is_available=False with the exact error.
    - Caches valid legs in RouteLegStore for offline repeatability.
    """
    # 1. Coordinate validation
    if not (-90.0 <= origin_lat <= 90.0 and -180.0 <= origin_lon <= 180.0):
        return DirectedRouteLeg(
            origin_id=origin_id, destination_id=destination_id, mode=mode,
            distance_meters=0.0, duration_seconds=0.0, distance_km=0.0, duration_minutes=0.0,
            is_available=False, failure_reason=f"INVALID_COORDINATES: Origin ({origin_lat}, {origin_lon}) is out of bounds."
        )
    if not (-90.0 <= destination_lat <= 90.0 and -180.0 <= destination_lon <= 180.0):
        return DirectedRouteLeg(
            origin_id=origin_id, destination_id=destination_id, mode=mode,
            distance_meters=0.0, duration_seconds=0.0, distance_km=0.0, duration_minutes=0.0,
            is_available=False, failure_reason=f"INVALID_COORDINATES: Destination ({destination_lat}, {destination_lon}) is out of bounds."
        )

    if mode == TransportMode.WALKING and os.environ.get("CULTUREROUTE_WALKING_PROFILE_VERIFIED") != "1":
        return DirectedRouteLeg(origin_id, destination_id, mode, 0, 0, 0, 0, False,
                                failure_reason="WALKING_PROFILE_UNVERIFIED")

    # 2. Check local persistent cache
    if store:
        cached = store.get_cached_leg(origin_id, destination_id, mode,
                                      (origin_lat, origin_lon), (destination_lat, destination_lon))
        if cached:
            return cached

    # 3. Identity leg check
    if origin_id == destination_id or (origin_lat == destination_lat and origin_lon == destination_lon):
        leg = DirectedRouteLeg(
            origin_id=origin_id,
            destination_id=destination_id,
            mode=mode,
            distance_meters=0.0,
            duration_seconds=0.0,
            distance_km=0.0,
            duration_minutes=0.0,
            is_available=True,
            polyline_points=[(origin_lat, origin_lon)],
            source_name="CultureRoute Identity Routing (Same Location)"
        )
        return leg

    # 4. Straight-line proximity check for walking mode threshold
    straight_km = haversine_distance_km(origin_lat, origin_lon, destination_lat, destination_lon)
    if mode == TransportMode.WALKING and straight_km > MAX_WALKING_DISTANCE_KM:
        leg = DirectedRouteLeg(
            origin_id=origin_id,
            destination_id=destination_id,
            mode=mode,
            distance_meters=round(straight_km * 1000.0, 1),
            duration_seconds=0.0,
            distance_km=round(straight_km, 2),
            duration_minutes=0.0,
            is_available=False,
            failure_reason=f"UNREACHABLE_BY_MODE: Walking route distance ({straight_km:.1f} km straight-line) exceeds maximum realistic walking threshold ({MAX_WALKING_DISTANCE_KM} km)."
        )
        return leg

    # 5. Query genuine routing provider if network is allowed
    configured_url = provider_url or configured_backend(mode)
    if not configured_url or not allow_network:
        return DirectedRouteLeg(origin_id, destination_id, mode, 0, 0, 0, 0, False,
                                failure_reason="ROUTING_PROVIDER_UNAVAILABLE: configure a matching OSRM profile")
    base_url = configured_url.rstrip("/")
    profile = "driving" if mode == TransportMode.DRIVING else "foot"
    request_url = f"{base_url}/route/v1/{profile}/{origin_lon:.6f},{origin_lat:.6f};{destination_lon:.6f},{destination_lat:.6f}?overview=full&geometries=geojson"

    if allow_network:
        try:
            requested_at = datetime.now(timezone.utc).isoformat()
            resp = requests.get(
                request_url,
                headers={"User-Agent": "CultureRouteRoutingEngine/2.0 (AcademicResearch; IndiaCatalog)"},
                timeout=DEFAULT_ROUTING_TIMEOUT
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    r = data["routes"][0]
                    dist_m = float(r["distance"])
                    dur_s = float(r["duration"])
                    geom_pts = r.get("geometry", {}).get("coordinates", [])
                    lat_lon_pts = [(float(pt[1]), float(pt[0])) for pt in geom_pts]

                    dist_km = round(dist_m / 1000.0, 2)

                    dur_min = round(dur_s / 60.0, 1)
                    if (not math.isfinite(dist_m) or not math.isfinite(dur_s) or dist_m <= 0 or dur_s <= 0 or
                            len(lat_lon_pts) < 3 or
                            any(not math.isfinite(lat) or not math.isfinite(lon) or
                                not -90 <= lat <= 90 or not -180 <= lon <= 180
                                for lat, lon in lat_lon_pts) or
                            haversine_distance_km(origin_lat, origin_lon, *lat_lon_pts[0]) > 2 or
                            haversine_distance_km(destination_lat, destination_lon, *lat_lon_pts[-1]) > 2 or
                            dist_km < straight_km * 0.95):
                        return DirectedRouteLeg(origin_id, destination_id, mode, 0, 0, 0, 0, False,
                                                failure_reason="INVALID_ROUTE_RESPONSE")

                    if mode == TransportMode.WALKING and dist_km > MAX_WALKING_DISTANCE_KM:
                        leg = DirectedRouteLeg(
                            origin_id=origin_id,
                            destination_id=destination_id,
                            mode=mode,
                            distance_meters=dist_m,
                            duration_seconds=dur_s,
                            distance_km=dist_km,
                            duration_minutes=dur_min,
                            is_available=False,
                            failure_reason=f"UNREACHABLE_BY_MODE: Walking route distance ({dist_km:.1f} km) exceeds maximum realistic walking threshold ({MAX_WALKING_DISTANCE_KM} km).",
                            polyline_points=lat_lon_pts,
                            source_name=f"OSRM Directed Routing ({base_url})",
                            source_version="v5.27.1"
                        )
                        return leg

                    leg = DirectedRouteLeg(
                        origin_id=origin_id,
                        destination_id=destination_id,
                        mode=mode,
                        distance_meters=round(dist_m, 1),
                        duration_seconds=round(dur_s, 1),
                        distance_km=dist_km,
                        duration_minutes=dur_min,
                        is_available=True,
                        polyline_points=lat_lon_pts,
                        source_name=f"OSRM Directed Routing ({base_url})",
                        source_version="OSRM API v1",
                        provider_url=base_url,
                        data_version=os.environ.get("CULTUREROUTE_ROUTING_DATA_VERSION", "unreported"),
                        origin_lat=origin_lat, origin_lon=origin_lon,
                        destination_lat=destination_lat, destination_lon=destination_lon,
                        requested_at=requested_at,
                        responded_at=datetime.now(timezone.utc).isoformat()
                    )
                    if store:
                        store.insert_leg(leg)
                    return leg
                else:
                    msg = data.get("message", "No route found on mapped road network")
                    leg = DirectedRouteLeg(
                        origin_id=origin_id, destination_id=destination_id, mode=mode,
                        distance_meters=0.0, duration_seconds=0.0, distance_km=0.0, duration_minutes=0.0,
                        is_available=False, failure_reason=f"NO_ROAD_ROUTE: OSRM reported: {msg}"
                    )
                    return leg
            else:
                err_msg = f"HTTP {resp.status_code}: {resp.text[:120]}"
        except Exception as e:
            err_msg = f"Connection failed: {e}"
    else:
        err_msg = "Network disabled and no cached route exists."

    # In Phase 8, failure is explicitly reported rather than inventing a fabricated duration
    leg = DirectedRouteLeg(
        origin_id=origin_id,
        destination_id=destination_id,
        mode=mode,
        distance_meters=0.0,
        duration_seconds=0.0,
        distance_km=0.0,
        duration_minutes=0.0,
        is_available=False,
        failure_reason=f"ROUTING_PROVIDER_UNAVAILABLE: Could not compute directed route via '{base_url}'. Reason: {err_msg}"
    )
    return leg
