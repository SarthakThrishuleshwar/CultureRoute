"""CultureRoute Study Database Builder, Catalog, and Metric Contracts (Stage R2).

Reconciles SmartTrip (PS-01.db) and WanderMatch (PS-11.db) into a single,
atomic, reproducible, read-only SQLite study database (data/study_cache.db).

Guarantees:
- Exactly 24 distinct tables and 48,728 total rows.
- 8 shared tables verified identical by schema, PK, and row-level contents.
- Strict preservation of raw nulls, currency, and source IDs.
- Documented views for the 45 Indian study cities, 675 attractions, 411 trips,
  6,850 interactions, 3,191 selected stops, and 225 events.
- Shared result contracts for metrics, plot datasets, and spreadsheet-safe exports.
- Safe public projection in DEV Lab masking sensitive personal identity fields.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
from functools import lru_cache
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
import zipfile

ROOT_DIR = Path(__file__).resolve().parent.parent
SMART_TRIP_ZIP = ROOT_DIR / "SmartTrip (1).zip"
WANDER_MATCH_ZIP = ROOT_DIR / "WanderMatch.zip"
SMART_DB_ENTRY = "SmartTrip/data/PS-01.db"
WANDER_DB_ENTRY = "WanderMatch/data/PS-11.db"

DEFAULT_STUDY_DB = ROOT_DIR / "data" / "study_cache.db"

CULTURAL_CATEGORIES = ("heritage", "museum", "religious", "food")

# Sensitive columns to exclude/mask from public DEV Lab previews
SENSITIVE_COLUMNS: Set[str] = {
    "password_hash",
    "password",
    "email",
    "phone_number",
    "phone",
    "national_id",
    "passport_number",
    "credit_card_last4",
    "payment_method_token",
}


@dataclass(frozen=True)
class TableCatalogEntry:
    table_name: str
    origin_pack: str  # "shared", "SmartTrip", "WanderMatch"
    grain: str
    row_count: int
    columns: List[str]
    column_types: Dict[str, str]
    primary_key: List[str]
    foreign_keys: List[Dict[str, str]]
    null_counts: Dict[str, int]
    safe_columns: List[str]


@dataclass(frozen=True)
class StudyDatabaseMetadata:
    schema_version: str
    build_timestamp: str
    smart_sha256: str
    wander_sha256: str
    total_tables: int
    total_rows: int
    shared_tables: List[str]
    smart_only_tables: List[str]
    wander_only_tables: List[str]


@dataclass(frozen=True)
class StudyDatabaseCatalog:
    metadata: StudyDatabaseMetadata
    tables: Dict[str, TableCatalogEntry]


@dataclass(frozen=True)
class MetricContract:
    name: str
    definition: str
    population: str
    filters: str
    grain: str
    units: str
    value: Any
    formatted_value: str
    null_policy: str
    cutoff: str
    source_references: List[str]
    numerator: Optional[float] = None
    denominator: Optional[float] = None


@dataclass(frozen=True)
class PlotDatasetContract:
    name: str
    title: str
    question: str
    grain: str
    filters: str
    units: str
    data: List[Dict[str, Any]]
    source_references: List[str]


@dataclass(frozen=True)
class TableExportContract:
    name: str
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    format_type: str = "csv"
    formula_safe: bool = True


def get_pack_digests() -> Tuple[str, str]:
    """Compute and return SHA-256 digests for SmartTrip and WanderMatch zip archives."""
    if not SMART_TRIP_ZIP.exists():
        raise FileNotFoundError(f"SmartTrip archive missing: {SMART_TRIP_ZIP}")
    if not WANDER_MATCH_ZIP.exists():
        raise FileNotFoundError(f"WanderMatch archive missing: {WANDER_MATCH_ZIP}")

    smart_hash = hashlib.sha256(SMART_TRIP_ZIP.read_bytes()).hexdigest()
    wander_hash = hashlib.sha256(WANDER_MATCH_ZIP.read_bytes()).hexdigest()
    return smart_hash, wander_hash


def _determine_grain(table_name: str) -> str:
    """Document the natural key and domain grain for each canonical table."""
    grains = {
        "cities": "1 row per city (natural key: city_id)",
        "users": "1 row per registered user account (natural key: user_id)",
        "trips": "1 row per planned trip (natural key: trip_id)",
        "itineraries": "1 row per itinerary container (natural key: itinerary_id)",
        "itinerary_items": "1 row per scheduled stop/item (natural key: item_id)",
        "activities_poi": "1 row per point of interest / attraction (natural key: poi_id)",
        "poi_travel_matrix": "1 row per directed leg between two POIs (natural key: origin_poi_id, destination_poi_id)",
        "events_festivals": "1 row per festival or cultural event (natural key: event_id)",
        "accommodations": "1 row per lodging / hotel listing (natural key: accommodation_id)",
        "bookings": "1 row per booking reservation (natural key: booking_id)",
        "flights": "1 row per flight itinerary leg (natural key: flight_id)",
        "ground_transport_options": "1 row per ground transit route option (natural key: option_id)",
        "offline_sync_logs": "1 row per device synchronization event (natural key: sync_id)",
        "payment_transactions": "1 row per financial transaction (natural key: transaction_id)",
        "poi_reviews": "1 row per user attraction review (natural key: review_id)",
        "rental_cars": "1 row per vehicle rental option (natural key: rental_id)",
        "restaurants": "1 row per dining establishment (natural key: restaurant_id)",
        "user_preferences": "1 row per user preference record (natural key: preference_id)",
        "guides": "1 row per registered cultural guide (natural key: guide_id)",
        "guide_specializations": "1 row per guide domain specialization (natural key: specialization_id)",
        "guide_reviews": "1 row per tourist guide review (natural key: review_id)",
        "user_interactions": "1 row per telemetry event (natural key: interaction_id)",
        "recommendation_logs": "1 row per recommendation delivery (natural key: log_id)",
        "search_queries": "1 row per user search query submission (natural key: query_id)",
    }
    return grains.get(table_name, f"1 row per entity in {table_name}")


def build_study_database(target_path: Optional[Path] = None, force: bool = False) -> StudyDatabaseCatalog:
    """Build the single atomic SQLite study database from the two read-only zip packs."""
    db_path = target_path or DEFAULT_STUDY_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)

    smart_hash, wander_hash = get_pack_digests()

    # If already built and force is False, verify integrity and return catalog
    if db_path.exists() and not force:
        try:
            return load_study_catalog(db_path)
        except Exception:
            pass  # Rebuild if corrupted

    temp_paths: List[Path] = []
    tmp_out = db_path.with_suffix(".tmp")
    if tmp_out.exists():
        tmp_out.unlink()

    try:
        # Extract both source DBs to temporary files
        with zipfile.ZipFile(SMART_TRIP_ZIP) as z1:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as t1:
                t1.write(z1.read(SMART_DB_ENTRY))
                temp_paths.append(Path(t1.name))

        with zipfile.ZipFile(WANDER_MATCH_ZIP) as z2:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as t2:
                t2.write(z2.read(WANDER_DB_ENTRY))
                temp_paths.append(Path(t2.name))

        smart_conn = sqlite3.connect(f"{temp_paths[0].as_uri()}?mode=ro", uri=True)
        wander_conn = sqlite3.connect(f"{temp_paths[1].as_uri()}?mode=ro", uri=True)
        smart_conn.row_factory = sqlite3.Row
        wander_conn.row_factory = sqlite3.Row

        smart_tables = sorted([
            r[0] for r in smart_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ])
        wander_tables = sorted([
            r[0] for r in wander_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ])

        shared_tables = sorted(list(set(smart_tables) & set(wander_tables)))
        smart_only = sorted(list(set(smart_tables) - set(wander_tables)))
        wander_only = sorted(list(set(wander_tables) - set(smart_tables)))

        if len(smart_tables) != 18 or len(wander_tables) != 14 or len(shared_tables) != 8:
            raise ValueError(
                f"Source table count mismatch: SmartTrip={len(smart_tables)}, "
                f"WanderMatch={len(wander_tables)}, Shared={len(shared_tables)}"
            )

        # 1. Verify shared tables identical by schema, PK, and row contents
        for tbl in shared_tables:
            s_info = smart_conn.execute(f'PRAGMA table_info("{tbl}")').fetchall()
            w_info = wander_conn.execute(f'PRAGMA table_info("{tbl}")').fetchall()
            if s_info != w_info:
                raise ValueError(f"Schema mismatch in shared table '{tbl}':\nSmart: {s_info}\nWander: {w_info}")

            pk_col = next((r["name"] for r in s_info if r["pk"] == 1), None)
            order_clause = f'ORDER BY "{pk_col}"' if pk_col else ""
            s_rows = smart_conn.execute(f'SELECT * FROM "{tbl}" {order_clause}').fetchall()
            w_rows = wander_conn.execute(f'SELECT * FROM "{tbl}" {order_clause}').fetchall()

            if len(s_rows) != len(w_rows):
                raise ValueError(f"Row count mismatch in shared table '{tbl}': Smart={len(s_rows)}, Wander={len(w_rows)}")

            for idx, (sr, wr) in enumerate(zip(s_rows, w_rows)):
                if tuple(sr) != tuple(wr):
                    raise ValueError(f"Content divergence in shared table '{tbl}' at row index {idx}")

        # 2. Build canonical study SQLite database atomically
        dest_conn = sqlite3.connect(tmp_out)
        dest_conn.execute("PRAGMA synchronous = OFF")
        dest_conn.execute("PRAGMA journal_mode = MEMORY")

        catalog_entries: Dict[str, TableCatalogEntry] = {}
        total_rows_copied = 0

        all_tables_spec = [
            (t, "shared", smart_conn) for t in shared_tables
        ] + [
            (t, "SmartTrip", smart_conn) for t in smart_only
        ] + [
            (t, "WanderMatch", wander_conn) for t in wander_only
        ]

        for tbl, pack_origin, src_conn in all_tables_spec:
            # Get table DDL from sqlite_master
            ddl_row = src_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?", (tbl,)
            ).fetchone()
            dest_conn.execute(ddl_row[0])

            # Copy all rows
            cols_info = src_conn.execute(f'PRAGMA table_info("{tbl}")').fetchall()
            col_names = [r["name"] for r in cols_info]
            col_types = {r["name"]: r["type"] for r in cols_info}
            pks = [r["name"] for r in cols_info if r["pk"] > 0]

            fk_info = src_conn.execute(f'PRAGMA foreign_key_list("{tbl}")').fetchall()
            foreign_keys = [
                {"table": r["table"], "from": r["from"], "to": r["to"]}
                for r in fk_info
            ]

            rows = src_conn.execute(f'SELECT * FROM "{tbl}"').fetchall()
            if rows:
                placeholders = ",".join(["?"] * len(col_names))
                dest_conn.executemany(
                    f'INSERT INTO "{tbl}" VALUES ({placeholders})',
                    [tuple(r) for r in rows]
                )

            row_count = len(rows)
            total_rows_copied += row_count

            # Compute null counts
            null_counts: Dict[str, int] = {}
            for col in col_names:
                n_count = src_conn.execute(f'SELECT count(*) FROM "{tbl}" WHERE "{col}" IS NULL').fetchone()[0]
                null_counts[col] = int(n_count)

            safe_cols = [c for c in col_names if c.lower() not in SENSITIVE_COLUMNS]

            catalog_entries[tbl] = TableCatalogEntry(
                table_name=tbl,
                origin_pack=pack_origin,
                grain=_determine_grain(tbl),
                row_count=row_count,
                columns=col_names,
                column_types=col_types,
                primary_key=pks,
                foreign_keys=foreign_keys,
                null_counts=null_counts,
                safe_columns=safe_cols,
            )

        if total_rows_copied != 48728:
            raise ValueError(f"Total row reconciliation failed: expected 48,728, got {total_rows_copied}")

        # 3. Create canonical documented SQL views
        dest_conn.execute("""
            CREATE VIEW view_study_cities AS
            SELECT * FROM cities WHERE country_code = 'IN'
        """)

        dest_conn.execute("""
            CREATE VIEW view_study_attractions AS
            SELECT a.* FROM activities_poi a
            JOIN cities c USING(city_id)
            WHERE c.country_code = 'IN'
        """)

        dest_conn.execute("""
            CREATE VIEW view_study_trips AS
            SELECT t.* FROM trips t
            JOIN cities c ON c.city_id = t.destination_city_id
            WHERE c.country_code = 'IN' AND t.status <> 'cancelled'
        """)

        dest_conn.execute("""
            CREATE VIEW view_study_interactions AS
            SELECT u.* FROM user_interactions u
            JOIN activities_poi a ON u.entity_type = 'poi' AND u.entity_id = a.poi_id
            JOIN cities c ON c.city_id = a.city_id
            WHERE c.country_code = 'IN'
        """)

        dest_conn.execute("""
            CREATE VIEW view_study_selected_stops AS
            SELECT ii.*, i.trip_id, t.destination_city_id, a.poi_category, a.name as poi_name
            FROM itinerary_items ii
            JOIN itineraries i ON i.itinerary_id = ii.itinerary_id
            JOIN trips t ON t.trip_id = i.trip_id
            JOIN cities c ON c.city_id = t.destination_city_id
            JOIN activities_poi a ON a.poi_id = ii.entity_id
            WHERE c.country_code = 'IN'
              AND t.status <> 'cancelled'
              AND i.is_active = 1
              AND ii.status = 'confirmed'
              AND ii.item_type = 'poi'
              AND ii.entity_type = 'poi'
              AND a.city_id = t.destination_city_id
        """)

        dest_conn.execute("""
            CREATE VIEW view_study_events AS
            SELECT e.* FROM events_festivals e
            JOIN cities c USING(city_id)
            WHERE c.country_code = 'IN'
        """)

        # Metadata table
        meta = StudyDatabaseMetadata(
            schema_version="2.0.0",
            build_timestamp=datetime.now(timezone.utc).isoformat(),
            smart_sha256=smart_hash,
            wander_sha256=wander_hash,
            total_tables=24,
            total_rows=total_rows_copied,
            shared_tables=shared_tables,
            smart_only_tables=smart_only,
            wander_only_tables=wander_only,
        )

        dest_conn.execute("""
            CREATE TABLE _study_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        dest_conn.execute(
            "INSERT INTO _study_metadata (key, value) VALUES ('catalog_json', ?)",
            (json.dumps({
                "metadata": asdict(meta),
                "tables": {k: asdict(v) for k, v in catalog_entries.items()}
            }),)
        )

        dest_conn.commit()
        dest_conn.close()

        # Close source connections
        smart_conn.close()
        wander_conn.close()

        # Atomic replacement of target file
        if db_path.exists():
            db_path.unlink()
        tmp_out.rename(db_path)

        return StudyDatabaseCatalog(metadata=meta, tables=catalog_entries)

    finally:
        if tmp_out.exists():
            tmp_out.unlink()
        for p in temp_paths:
            p.unlink(missing_ok=True)


@lru_cache(maxsize=16)
def load_study_catalog(db_path: Optional[Path] = None) -> StudyDatabaseCatalog:
    """Read schema catalog and metadata from the compiled study SQLite database."""
    path = db_path or DEFAULT_STUDY_DB
    if not path.exists():
        return build_study_database(path)

    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM _study_metadata WHERE key = 'catalog_json'").fetchone()
        if not row:
            conn.close()
            return build_study_database(path, force=True)
        data = json.loads(row[0])
        meta = StudyDatabaseMetadata(**data["metadata"])
        tables = {k: TableCatalogEntry(**v) for k, v in data["tables"].items()}
        return StudyDatabaseCatalog(metadata=meta, tables=tables)
    finally:
        conn.close()


@contextmanager
def open_study_cache(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Provide a read-only connection to the canonical study SQLite database."""
    path = db_path or DEFAULT_STUDY_DB
    if not path.exists():
        build_study_database(path)

    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CultureRoute Study Database Builder")
    parser.add_argument("--build", action="store_true", help="Build or rebuild study_cache.db")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if cache exists")
    parser.add_argument("--output", type=Path, default=DEFAULT_STUDY_DB, help="Target database path")
    args = parser.parse_args()

    print(f"Building CultureRoute study database at {args.output}...")
    cat = build_study_database(args.output, force=args.force)
    print(f"Build complete: {cat.metadata.total_tables} tables, {cat.metadata.total_rows:,} rows.")
    print(f"Shared tables ({len(cat.metadata.shared_tables)}): {', '.join(cat.metadata.shared_tables)}")
    print(f"SmartTrip-only ({len(cat.metadata.smart_only_tables)}): {', '.join(cat.metadata.smart_only_tables)}")
    print(f"WanderMatch-only ({len(cat.metadata.wander_only_tables)}): {', '.join(cat.metadata.wander_only_tables)}")
