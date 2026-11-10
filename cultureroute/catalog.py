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
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -64000")  # 64 MB page cache
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
                CREATE TABLE IF NOT EXISTS extract_registry (
                    extract_id TEXT PRIMARY KEY,
                    zone_name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    extract_date TEXT NOT NULL,
                    import_date TEXT NOT NULL,
                    rows_settlements INTEGER NOT NULL DEFAULT 0,
                    rows_places INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL,
                    error_message TEXT
                );
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

    def record_extract_status(
        self,
        extract_id: str,
        zone_name: str,
        filename: str,
        status: str,
        extract_date: str,
        import_date: str,
        rows_settlements: int = 0,
        rows_places: int = 0,
        sha256: str = "",
        error_message: Optional[str] = None
    ) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO extract_registry (
                    extract_id, zone_name, filename, status, extract_date, import_date,
                    rows_settlements, rows_places, sha256, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                extract_id, zone_name, filename, status, extract_date, import_date,
                rows_settlements, rows_places, sha256, error_message
            ))

    def get_extract_registry(self) -> List[Dict[str, object]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM extract_registry ORDER BY import_date ASC, zone_name ASC").fetchall()
            return [dict(r) for r in rows]

    def insert_settlement(self, s: RealSettlement) -> None:
        self.insert_settlements_batch([s])

    def insert_settlements_batch(self, settlements: List[RealSettlement]) -> None:
        if not settlements:
            return
        params = [
            (
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
            )
            for s in settlements
        ]
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO settlements (
                    settlement_id, name, name_lower, local_names_json, state, district,
                    sub_district, settlement_type, latitude, longitude, source_name,
                    source_url, source_record_id, extract_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, params)

    def insert_place(self, p: RealPlaceRecord) -> None:
        self.insert_places_batch([p])

    def insert_places_batch(self, places: List[RealPlaceRecord]) -> None:
        if not places:
            return
        params = [
            (
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
            )
            for p in places
        ]
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO places (
                    source_id, upstream_type, upstream_id, name, local_names_json,
                    latitude, longitude, state, district, sub_district, settlement_type,
                    cultural_category, subcategory, raw_tags_json, source_url,
                    source_extract_date, import_date, last_checked_date,
                    opening_hours_json, entry_fee_json, accessibility_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, params)

    def search_settlements(self, query: str) -> List[RealSettlement]:
        """Search settlements by name or alternate/local names with substring matching and state disambiguation."""
        clean_q = query.lower().strip()
        if not clean_q:
            return []

        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM settlements
                WHERE name_lower = ? OR name_lower LIKE ? OR local_names_json LIKE ?
                ORDER BY CASE
                    WHEN name_lower = ? THEN 0
                    WHEN name_lower LIKE ? THEN 1
                    ELSE 2
                END,
                CASE
                    WHEN settlement_type IN ('city', 'town') THEN 0
                    WHEN settlement_type IN ('village') THEN 1
                    ELSE 2
                END,
                CASE
                    WHEN state != 'India' AND state != '' THEN 0
                    ELSE 1
                END,
                name ASC
                LIMIT 50
            """, (clean_q, f"{clean_q}%", f"%{clean_q}%", clean_q, f"{clean_q}%")).fetchall()

            return [self._row_to_settlement(r) for r in rows]

    def get_settlement_by_id(self, settlement_id: str) -> Optional[RealSettlement]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM settlements WHERE settlement_id = ?", (settlement_id,)).fetchone()
            if row:
                return self._row_to_settlement(row)
            return None

    def get_place_by_id(self, source_id: str) -> Optional[RealPlaceRecord]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM places WHERE source_id = ?", (source_id,)).fetchone()
            if row:
                return self._row_to_place(row)
            return None

    def search_nearby_places(
        self,
        lat: float,
        lon: float,
        radius_km: float = 30.0,
        category: Optional[CulturalCategory] = None,
        deduplicate: bool = True
    ) -> List[Tuple[RealPlaceRecord, float]]:
        """Search places within a radius using bounding-box filtering and haversine distance.

        Returns a list of (RealPlaceRecord, distance_km) ordered by proximity.
        If deduplicate=True, near-duplicate records (same normalized name within 2 km, e.g. a complex
        and its duplicate/constituent UNESCO centroid) are deduplicated, keeping the most specific/detailed
        record while preserving upstream IDs in the database.
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

        if not deduplicate or len(results) <= 1:
            return results

        # Deduplicate near-duplicates with matching normalized names within 2.0 km
        # IMPORTANT: Protect distinct constituent attractions from merging with parent complexes.
        # Merging only occurs when:
        # 1. Distance <= 2.0 km, AND
        # 2. Both venues are the exact same venue under duplicate source IDs (e.g. duplicate Wikidata or OSM node/way)
        #    where the core distinctive nouns match exactly, OR one is an explicit centroid with identical name.
        # Distinct constituent structures (e.g. 'Kandariya Mahadeva Temple' vs 'Khajuraho Group of Monuments')
        # have specific identifying words and MUST be kept distinct.
        import re
        def _tokenize_name(name: str) -> set[str]:
            clean = re.sub(r"[,\-\(\)\'\"]", " ", name.lower())
            stop = {"the", "of", "at", "in", "and", "a", "an", "group", "monuments", "complex", "site", "places"}
            return {t for t in clean.split() if t not in stop and len(t) > 2}

        # Words designating specific constituent buildings/shrines
        constituent_designators = {
            "kandariya", "lakshmana", "varaha", "duladeo", "matangeshwar", "chaturbhuj",
            "parshvanatha", "adinatha", "ghantai", "shantinatha", "javari", "vamana",
            "chasing", "natamandira", "bhogamandapa", "jagannath", "mayadevi", "chhaya"
        }

        deduped: List[Tuple[RealPlaceRecord, float]] = []
        for place, dist in results:
            p_tokens = _tokenize_name(place.name)
            is_dup = False
            for existing_p, existing_dist in deduped:
                # If within 2.0 km
                if haversine_distance_km(place.latitude, place.longitude, existing_p.latitude, existing_p.longitude) <= 2.0:
                    e_tokens = _tokenize_name(existing_p.name)

                    # Check for constituent site vs complex: if one contains a constituent designator not in the other, DO NOT MERGE
                    p_const = p_tokens & constituent_designators
                    e_const = e_tokens & constituent_designators
                    if p_const != e_const:
                        continue

                    # Exact token match -> confirmed duplicate
                    if p_tokens and e_tokens and p_tokens == e_tokens:
                        is_dup = True
                        break

                    # One name is an exact subset of the other, but both share the core proper noun (e.g. "Konark Sun Temple" and "Sun Temple, Konark")
                    core_proper = p_tokens & e_tokens
                    # Require at least one substantial proper noun (length >= 4) that is not a generic descriptor or test artifact
                    generics = {"sun", "temple", "temples", "monument", "monuments", "palace", "fort", "mosque", "church", "monastery", "mahal", "test", "synthetic"}
                    substantive_common = [t for t in core_proper if t not in generics and len(t) >= 4]

                    if substantive_common:
                        # If both are essentially describing the exact same monument
                        non_common_p = [t for t in (p_tokens - core_proper) if t not in generics]
                        non_common_e = [t for t in (e_tokens - core_proper) if t not in generics]
                        if not non_common_p and not non_common_e:
                            is_dup = True
                            break

            if not is_dup:
                deduped.append((place, dist))

        return deduped

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
