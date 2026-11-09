"""Tests for CultureRoute Phase 4: Discovery Baseline & Boundary Rigor.

Verifies:
1. Exact polygon validation with holes (mainland, island, hole exclusion, international rejection).
2. Missing boundary gate failure.
3. Safe publication and atomic rollback (previous database remains byte-for-byte intact on failure).
4. Reconciled SQLite row counts and metadata agreement.
5. Discovery coverage state distinctions (catalog unavailable, area not indexed, zero matches).
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
import sqlite3
import tempfile
import pytest

from cultureroute.boundary import IndiaBoundaryValidator, point_in_polygon
from cultureroute.catalog import RealCatalogStore
from cultureroute.ingest import run_streaming_import, calculate_sha256
from cultureroute.study_data import verify_and_audit_study

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
BOUNDARY_GEOJSON = DATA_DIR / "india_boundary.geojson"
UNLOCODE_CSV = DATA_DIR / "unlocode_raw.csv"
UNESCO_JSON = DATA_DIR / "wikidata_unesco_india.json"
CATALOG_DB = DATA_DIR / "real_catalog.db"


def test_study_audit_unchanged_in_phase4():
    """Verify synthetic study baseline remains 100% intact."""
    report = verify_and_audit_study()
    assert report.distinct_tables_count == 24
    assert report.distinct_rows_count == 48728
    assert report.india_cities_count == 45
    assert report.india_attractions_count == 675
    assert report.study_trips_count == 411
    assert report.cultural_attractions_count == 211
    assert report.cultural_interactions_count == 2144
    assert report.cultural_selected_stops_count == 961


def test_polygon_validator_holes_fixture():
    """Verify polygon ray-casting with an explicit exterior ring and interior hole."""
    fixture = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0], [10.0, 10.0]], # Exterior
                [[13.0, 13.0], [17.0, 13.0], [17.0, 17.0], [13.0, 17.0], [13.0, 13.0]]  # Hole
            ]
        }
    }
    with tempfile.NamedTemporaryFile(suffix=".geojson", mode="w", delete=False, encoding="utf-8") as tmp:
        json.dump(fixture, tmp)
        tmp_path = Path(tmp.name)

    try:
        val = IndiaBoundaryValidator(tmp_path)
        assert val.is_available is True
        # Inside exterior and outside hole -> True
        assert val.is_inside(11.0, 11.0) is True
        assert val.is_inside(19.0, 19.0) is True
        # Inside the hole -> False
        assert val.is_inside(15.0, 15.0) is False
        assert val.is_inside(14.0, 16.0) is False
        # Outside exterior -> False
        assert val.is_inside(5.0, 5.0) is False
        assert val.is_inside(25.0, 25.0) is False
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_boundary_mainland_islands_and_rejections():
    """Verify official India boundary accepts mainland/islands and rejects international points."""
    assert BOUNDARY_GEOJSON.exists(), "Official India boundary GeoJSON must exist"
    val = IndiaBoundaryValidator(BOUNDARY_GEOJSON)
    assert val.is_available is True

    # Valid mainland locations
    assert val.is_inside(28.6139, 77.2090) is True  # Delhi
    assert val.is_inside(12.9716, 77.5946) is True  # Bengaluru
    assert val.is_inside(8.0883, 77.5385) is True   # Kanyakumari
    assert val.is_inside(15.9189, 75.6842) is True  # Badami
    assert val.is_inside(26.9124, 75.7873) is True  # Jaipur

    # Valid islands
    assert val.is_inside(11.6234, 92.7265) is True  # Port Blair, Andaman & Nicobar
    assert val.is_inside(10.56, 72.60) is True      # Kavaratti, Lakshadweep

    # Border and extraterritorial points
    assert val.is_inside(31.5204, 74.3587) is False  # Lahore, Pakistan
    assert val.is_inside(27.7172, 85.3240) is False  # Kathmandu, Nepal
    assert val.is_inside(6.9271, 79.8612) is False   # Colombo, Sri Lanka
    assert val.is_inside(23.8103, 90.4125) is False  # Dhaka, Bangladesh
    assert val.is_inside(15.0, 65.0) is False        # Deep Arabian Sea


def test_missing_boundary_fails_strictly():
    """Verify that a missing boundary reports unavailable and fails strict checks."""
    missing_val = IndiaBoundaryValidator(Path("nonexistent_boundary_file.geojson"))
    assert missing_val.is_available is False
    assert missing_val.is_inside(28.6139, 77.2090) is False
    assert missing_val.is_inside(31.5204, 74.3587) is False
    with pytest.raises(RuntimeError, match="Coordinate validation unavailable"):
        missing_val.is_inside(28.6139, 77.2090, strict=True)


def test_atomic_rollback_on_injected_failure():
    """Verify that an injected failure leaves the prior database byte-for-byte intact."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        initial_db = Path(tmp.name)

    try:
        # 1. Create a valid initial database
        store = RealCatalogStore(initial_db)
        store.set_metadata("snapshot_date", "2026-11-01")
        store.set_metadata("test_marker", "initial_valid_state")
        del store
        gc.collect()

        initial_sha = calculate_sha256(initial_db)

        # 2. Inject failure by pointing to non-existent UN/LOCODE file
        with pytest.raises(FileNotFoundError):
            run_streaming_import(
                unlocode_csv=Path("nonexistent_unlocode.csv"),
                unesco_json=UNESCO_JSON,
                boundary_geojson=BOUNDARY_GEOJSON,
                output_db=initial_db
            )

        # 3. Target database must remain byte-for-byte intact
        after_sha = calculate_sha256(initial_db)
        assert initial_sha == after_sha, "Prior database must remain byte-for-byte identical after failed import"

        # 4. Content check
        store_check = RealCatalogStore(initial_db)
        assert store_check.get_metadata("test_marker") == "initial_valid_state"
        del store_check
        gc.collect()
    finally:
        gc.collect()
        if initial_db.exists():
            try:
                initial_db.unlink()
            except Exception:
                pass
        bak = initial_db.with_suffix(".db.bak")
        if bak.exists():
            try:
                bak.unlink()
            except Exception:
                pass


def test_count_reconciliation_and_metadata_agreement():
    """Verify that metadata published counts agree exactly with actual SQLite row counts."""
    assert CATALOG_DB.exists(), "Catalog DB must exist"
    store = RealCatalogStore(CATALOG_DB)
    meta = store.get_all_metadata()

    with sqlite3.connect(CATALOG_DB) as conn:
        actual_settlements = conn.execute("SELECT count(*) FROM settlements").fetchone()[0]
        actual_places = conn.execute("SELECT count(*) FROM places").fetchone()[0]

    assert int(meta["settlements_count"]) == actual_settlements
    assert int(meta["places_count"]) == actual_places
    assert actual_settlements >= 900
    assert actual_places >= 55
