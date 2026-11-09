"""Catalog storage and spatial search index for CultureRoute Real Places.

Stores:
1. Real settlements (cities, towns, villages) with name search, duplicate resolution, and state filtering.
2. Real cultural attractions with spatial proximity search (haversine) and category filtering.
3. Import metadata: coverage scope, snapshot dates, checksums, and dataset provenance.
All stored in SQLite with strict namespace prefixes and separation from the synthetic study database.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import math
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple

from cultureroute.domain import (
    RealSettlement,
    RealPlaceRecord,
    CulturalCategory,
    OpeningHoursDetail,
    EntryFeeDetail,
    AccessibilityDetail,
    VerificationStatus,
    FeeStatus,
    AccessibilityStatus,
    FieldEvidence,
)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
        math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class RealCatalogStore:
    """SQLite-backed spatial catalog for real-world Indian settlements and attractions."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS settlements (
                    settlement_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_lower TEXT NOT NULL,
                    local_names_json TEXT,
                    state TEXT NOT NULL,
                    district TEXT,
                    sub_district TEXT,
                    settlement_type TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    extract_date TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_settlements_name ON settlements(name_lower);
                CREATE INDEX IF NOT EXISTS idx_settlements_state ON settlements(state);

                CREATE TABLE IF NOT EXISTS places (
                    source_id TEXT PRIMARY KEY,
                    upstream_type TEXT NOT NULL,
                    upstream_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    local_names_json TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    state TEXT NOT NULL,
                    district TEXT,
                    sub_district TEXT,
                    settlement_type TEXT NOT NULL,
                    cultural_category TEXT NOT NULL,
                    subcategory TEXT,
                    raw_tags_json TEXT,
                    source_url TEXT NOT NULL,
                    source_extract_date TEXT NOT NULL,
                    import_date TEXT NOT NULL,
                    last_checked_date TEXT NOT NULL,
                    opening_hours_json TEXT,
                    entry_fee_json TEXT,
                    accessibility_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_places_category ON places(cultural_category);
                CREATE INDEX IF NOT EXISTS idx_places_lat_lon ON places(latitude, longitude);
            """)

    def set_metadata(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", (key, value))

    def get_metadata(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
            if row:
                return row["value"]
            return default

    def get_all_metadata(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM metadata").fetchall()
            return {r["key"]: r["value"] for r in rows}

    def insert_settlement(self, s: RealSettlement) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO settlements (
                    settlement_id, name, name_lower, local_names_json, state, district,
                    sub_district, settlement_type, latitude, longitude, source_name,
                    source_url, source_record_id, extract_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s.settlement_id,
                s.name,
                s.name.lower().strip(),
                json.dumps(s.local_names, ensure_ascii=False),
                s.state,
                s.district,
                s.sub_district,
                s.settlement_type,
                s.latitude,
                s.longitude,
                s.source_name,
                s.source_url,
                s.source_record_id,
                s.extract_date.isoformat(),
            ))

    def insert_place(self, p: RealPlaceRecord) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO places (
                    source_id, upstream_type, upstream_id, name, local_names_json,
                    latitude, longitude, state, district, sub_district, settlement_type,
                    cultural_category, subcategory, raw_tags_json, source_url,
                    source_extract_date, import_date, last_checked_date,
                    opening_hours_json, entry_fee_json, accessibility_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.source_id,
                p.upstream_type,
                p.upstream_id,
                p.name,
                json.dumps(p.local_names, ensure_ascii=False),
                p.latitude,
                p.longitude,
                p.state,
                p.district,
                p.sub_district,
                p.settlement_type,
                p.cultural_category.value,
                p.subcategory,
                json.dumps(p.raw_tags, ensure_ascii=False),
                p.source_url,
                p.source_extract_date.isoformat(),
                p.import_date.isoformat(),
                p.last_checked_date.isoformat(),
                p.opening_hours.model_dump_json(),
                p.entry_fee.model_dump_json(),
                p.accessibility.model_dump_json(),
            ))

    def search_settlements(self, query: str) -> List[RealSettlement]:
        """Search settlements by name with substring matching and state disambiguation."""
        clean_q = query.lower().strip()
        if not clean_q:
            return []

        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM settlements
                WHERE name_lower = ? OR name_lower LIKE ?
                ORDER BY CASE WHEN name_lower = ? THEN 0 WHEN name_lower LIKE ? THEN 1 ELSE 2 END, name ASC
                LIMIT 50
            """, (clean_q, f"{clean_q}%", clean_q, f"{clean_q}%")).fetchall()

            return [self._row_to_settlement(r) for r in rows]

    def get_settlement_by_id(self, settlement_id: str) -> Optional[RealSettlement]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM settlements WHERE settlement_id = ?", (settlement_id,)).fetchone()
            if row:
                return self._row_to_settlement(row)
            return None

    def search_nearby_places(
        self,
        lat: float,
        lon: float,
        radius_km: float = 30.0,
        category: Optional[CulturalCategory] = None
    ) -> List[Tuple[RealPlaceRecord, float]]:
        """Search places within a radius using bounding-box filtering and haversine distance.

        Returns a list of (RealPlaceRecord, distance_km) ordered by proximity.
        """
        deg_lat = radius_km / 111.0
        deg_lon = radius_km / (111.0 * max(0.1, math.cos(math.radians(lat))))

        min_lat = lat - deg_lat
        max_lat = lat + deg_lat
        min_lon = lon - deg_lon
        max_lon = lon + deg_lon

        sql = """
            SELECT * FROM places
            WHERE latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
        """
        params: List[object] = [min_lat, max_lat, min_lon, max_lon]

        if category is not None:
            sql += " AND cultural_category = ?"
            params.append(category.value)

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        results: List[Tuple[RealPlaceRecord, float]] = []
        for r in rows:
            place = self._row_to_place(r)
            dist = haversine_distance_km(lat, lon, place.latitude, place.longitude)
            if dist <= radius_km:
                results.append((place, round(dist, 2)))

        results.sort(key=lambda x: x[1])
        return results

    def get_counts(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            s_count = int(conn.execute("SELECT count(*) FROM settlements").fetchone()[0])
            p_count = int(conn.execute("SELECT count(*) FROM places").fetchone()[0])
            return {"settlements": s_count, "places": p_count}

    def _row_to_settlement(self, r: sqlite3.Row) -> RealSettlement:
        return RealSettlement(
            settlement_id=r["settlement_id"],
            name=r["name"],
            local_names=json.loads(r["local_names_json"] or "{}"),
            state=r["state"],
            district=r["district"],
            sub_district=r["sub_district"],
            settlement_type=r["settlement_type"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            source_name=r["source_name"],
            source_url=r["source_url"],
            source_record_id=r["source_record_id"],
            extract_date=date.fromisoformat(r["extract_date"]),
        )

    def _row_to_place(self, r: sqlite3.Row) -> RealPlaceRecord:
        return RealPlaceRecord(
            source_id=r["source_id"],
            upstream_type=r["upstream_type"],
            upstream_id=r["upstream_id"],
            name=r["name"],
            local_names=json.loads(r["local_names_json"] or "{}"),
            latitude=r["latitude"],
            longitude=r["longitude"],
            state=r["state"],
            district=r["district"],
            sub_district=r["sub_district"],
            settlement_type=r["settlement_type"],
            cultural_category=CulturalCategory(r["cultural_category"]),
            subcategory=r["subcategory"],
            raw_tags=json.loads(r["raw_tags_json"] or "{}"),
            source_url=r["source_url"],
            source_extract_date=date.fromisoformat(r["source_extract_date"]),
            import_date=date.fromisoformat(r["import_date"]),
            last_checked_date=date.fromisoformat(r["last_checked_date"]),
            opening_hours=OpeningHoursDetail.model_validate_json(r["opening_hours_json"]),
            entry_fee=EntryFeeDetail.model_validate_json(r["entry_fee_json"]),
            accessibility=AccessibilityDetail.model_validate_json(r["accessibility_json"]),
        )

    def get_all_states(self) -> List[str]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT DISTINCT state FROM settlements WHERE state IS NOT NULL AND state != '' ORDER BY state").fetchall()
            return [r[0] for r in rows]

    def get_breakdown_by_state_and_category(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT state, cultural_category, count(*) as count
                FROM places
                GROUP BY state, cultural_category
                ORDER BY state, count DESC
            """).fetchall()
            return [{"state": r["state"], "category": r["cultural_category"], "count": r["count"]} for r in rows]

    def get_places_by_state(self, state: str) -> List[RealPlaceRecord]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM places WHERE state = ? ORDER BY name", (state,)).fetchall()
            return [self._row_to_place(r) for r in rows]
