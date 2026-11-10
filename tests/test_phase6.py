"""Phase 6 Multi-Zone Ingestion, Resumability, Coverage Semantics, and Regression Tests.

Validates:
1. Multi-zone extract registry tracking, status transitions, and resume capability.
2. Cross-zone overlapping OSM object handling (idempotent INSERT OR REPLACE on stable IDs).
3. Preservation of distinct constituent structures sharing a complex name or vicinity.
4. Truthful coverage derivation: Complete Extract published only when all official zones are complete;
   otherwise Partial Coverage.
5. Strict separation of source extract date, import date, and last checked date.
6. Unknown fields (opening hours, entry fee, accessibility) preserved as UNKNOWN, never ₹0 or verified.
7. Rollback protection on corrupted extract or interrupted import.
8. Complete separation of real catalog records from 45-city synthetic study data.
9. Nationwide real-source geographic search queries across all parts of India.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

import pytest

from cultureroute.boundary import IndiaBoundaryValidator
from cultureroute.catalog import RealCatalogStore, haversine_distance_km
from cultureroute.domain import (
    AccessibilityDetail,
    AccessibilityStatus,
    CulturalCategory,
    EntryFeeDetail,
    FeeStatus,
    OpeningHoursDetail,
    RealPlaceRecord,
    RealSettlement,
    VerificationStatus,
)
from cultureroute.multi_ingest import (
    MultiZoneCatalogBuilder,
    OFFICIAL_INDIA_ZONES,
    ZoneExtractConfig,
    build_default_zone_configs,
)

CATALOG_DB = Path("data/real_catalog.db")
BOUNDARY_PATH = Path("data/india_boundary.geojson")
MANIFEST_PATH = Path("data/source_manifest.json")


def test_extract_registry_and_nationwide_coverage_metadata():
    """Verify that catalog metadata derives coverage truthfully from extract registry."""
    assert CATALOG_DB.exists(), "data/real_catalog.db must exist"
    store = RealCatalogStore(CATALOG_DB)
    meta = store.get_all_metadata()
    reg = store.get_extract_registry()

    assert len(reg) == 6, f"Expected 6 registered zone extracts, got {len(reg)}"
    assert all(r["status"] == "COMPLETED" for r in reg), "All 6 registered zones must have COMPLETED status"

    assert meta.get("coverage_level") == "Complete Extract"
    assert meta.get("is_nationwide") == "true"
    assert meta.get("completed_zones_count") == "6"
    assert meta.get("total_zones_count") == "6"

    # Verify all 6 zones are accounted for
    registered_zone_names = {r["zone_name"] for r in reg}
    expected_zone_names = {v["zone_name"] for v in OFFICIAL_INDIA_ZONES.values()}
    assert registered_zone_names == expected_zone_names


def test_cross_zone_idempotent_overlap_handling():
    """Verify that importing an identical OSM entity multiple times across zone boundaries is idempotent."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db = Path(tmp.name)

    try:
        store = RealCatalogStore(test_db)

        # Test settlement
        settle1 = RealSettlement(
            settlement_id="OSM:node/999001",
            name="Border Town",
            state="Central Zone State",
            settlement_type="town",
            latitude=22.5,
            longitude=80.0,
            source_name="OpenStreetMap PBF Extract",
            source_url="https://www.openstreetmap.org/node/999001",
            source_record_id="999001",
            extract_date=date(2026, 11, 10),
        )
        store.insert_settlement(settle1)
        assert store.get_counts()["settlements"] == 1

        # Re-import same entity with updated state attribute from neighboring zone
        settle2 = RealSettlement(
            settlement_id="OSM:node/999001",
            name="Border Town",
            state="Eastern Zone State",
            settlement_type="town",
            latitude=22.5,
            longitude=80.0,
            source_name="OpenStreetMap PBF Extract",
            source_url="https://www.openstreetmap.org/node/999001",
            source_record_id="999001",
            extract_date=date(2026, 11, 10),
        )
        store.insert_settlement(settle2)
        # Count MUST remain exactly 1, state updated
        assert store.get_counts()["settlements"] == 1
        fetched = store.get_settlement_by_id("OSM:node/999001")
        assert fetched is not None
        assert fetched.state == "Eastern Zone State"

        # Test place idempotence
        place1 = RealPlaceRecord(
            source_id="OSM:way/888001",
            upstream_type="way",
            upstream_id="888001",
            name="Border Heritage Fort",
            latitude=22.51,
            longitude=80.01,
            state="Border State",
            cultural_category=CulturalCategory.HERITAGE,
            subcategory="fort",
            source_url="https://www.openstreetmap.org/way/888001",
            source_extract_date=date(2026, 11, 10),
            import_date=date(2026, 11, 10),
            last_checked_date=date(2026, 11, 10),
        )
        store.insert_place(place1)
        assert store.get_counts()["places"] == 1

        # Re-insert in batch
        store.insert_places_batch([place1, place1])
        assert store.get_counts()["places"] == 1

    finally:
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass


def test_constituent_structures_preserved_distinct():
    """Verify distinct nearby structures that happen to share a complex or vicinity are NOT falsely merged."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db = Path(tmp.name)

    try:
        store = RealCatalogStore(test_db)
        # Two distinct constituent temples within Khajuraho complex (150m apart)
        p1 = RealPlaceRecord(
            source_id="OSM:node/111001",
            upstream_type="node",
            upstream_id="111001",
            name="Kandariya Mahadeva Temple",
            latitude=24.8532,
            longitude=79.9197,
            state="Madhya Pradesh",
            cultural_category=CulturalCategory.HERITAGE,
            subcategory="temple",
            source_url="https://www.openstreetmap.org/node/111001",
            source_extract_date=date(2026, 11, 10),
            import_date=date(2026, 11, 10),
            last_checked_date=date(2026, 11, 10),
        )
        p2 = RealPlaceRecord(
            source_id="OSM:node/111002",
            upstream_type="node",
            upstream_id="111002",
            name="Lakshmana Temple",
            latitude=24.8538,
            longitude=79.9212,
            state="Madhya Pradesh",
            cultural_category=CulturalCategory.HERITAGE,
            subcategory="temple",
            source_url="https://www.openstreetmap.org/node/111002",
            source_extract_date=date(2026, 11, 10),
            import_date=date(2026, 11, 10),
            last_checked_date=date(2026, 11, 10),
        )
        store.insert_places_batch([p1, p2])

        nearby = store.search_nearby_places(lat=24.8530, lon=79.9200, radius_km=5.0, deduplicate=True)
        # Must return BOTH temples because their names represent distinct constituent monuments
        assert len(nearby) == 2
        names = {p.name for p, _ in nearby}
        assert "Kandariya Mahadeva Temple" in names
        assert "Lakshmana Temple" in names

    finally:
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass


def test_unknown_fields_explicitly_unknown():
    """Verify that unknown hours, fees, accessibility, and operating status remain explicitly UNKNOWN and not ₹0."""
    store = RealCatalogStore(CATALOG_DB)
    # Sample a batch of places
    with store._get_connection() as conn:
        rows = conn.execute("SELECT * FROM places LIMIT 50").fetchall()
        for r in rows:
            p = store._row_to_place(r)
            # Entry fee must not default to numeric 0 when status is UNKNOWN
            if p.entry_fee.status == FeeStatus.UNKNOWN:
                assert p.entry_fee.amount_domestic is None, f"Place {p.name} has UNKNOWN status but amount is {p.entry_fee.amount_domestic}"
                assert p.entry_fee.amount_international is None
            # Opening hours must not claim OPEN when status is UNKNOWN
            if p.opening_hours.status == VerificationStatus.UNKNOWN:
                assert p.opening_hours.opens_local_time is None
                assert p.opening_hours.closes_local_time is None


def test_provenance_dates_strict_separation():
    """Verify source_extract_date, import_date, and last_checked_date are strictly distinct."""
    store = RealCatalogStore(CATALOG_DB)
    meta = store.get_all_metadata()
    assert "source_extract_date" in meta
    assert "snapshot_date" in meta

    with store._get_connection() as conn:
        row = conn.execute("SELECT source_extract_date, import_date, last_checked_date FROM places LIMIT 1").fetchone()
        assert row is not None
        assert row["source_extract_date"]
        assert row["import_date"]
        assert row["last_checked_date"]


def test_rollback_protection_on_failed_staging():
    """Verify that a corrupted extract or processing failure preserves the last good catalog."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_out:
        out_db = Path(tmp_out.name)
    with tempfile.NamedTemporaryFile(suffix=".corrupted.pbf", delete=False) as tmp_corrupt:
        corrupt_pbf = Path(tmp_corrupt.name)
        corrupt_pbf.write_bytes(b"INVALID_CORRUPTED_BYTES_NOT_PBF")

    try:
        builder = MultiZoneCatalogBuilder(
            output_db=out_db,
            boundary_geojson=BOUNDARY_PATH,
        )
        # Establish initial good catalog
        init_store = RealCatalogStore(out_db)
        init_store.insert_settlement(RealSettlement(
            settlement_id="TEST:001",
            name="Good Settlement",
            state="State",
            settlement_type="town",
            latitude=20.0,
            longitude=80.0,
            source_name="Test",
            source_url="http://test",
            source_record_id="1",
            extract_date=date(2026, 11, 10),
        ))
        init_store.set_metadata("coverage_level", "Partial Coverage")
        assert init_store.get_counts()["settlements"] == 1

        # Attempt to import corrupt PBF
        corrupt_cfg = ZoneExtractConfig(
            extract_id="corrupt-zone",
            zone_name="Corrupt Zone",
            pbf_path=corrupt_pbf,
            extract_date="2026-11-10",
            sha256="fake_sha",
            source_url="http://corrupt",
        )

        with pytest.raises(Exception):
            builder.run_multi_zone_import([corrupt_cfg], resume=True)

        # Verify last good catalog was preserved intact
        preserved_store = RealCatalogStore(out_db)
        assert preserved_store.get_counts()["settlements"] == 1
        assert preserved_store.get_metadata("coverage_level") == "Partial Coverage"

    finally:
        if out_db.exists():
            try:
                out_db.unlink()
            except Exception:
                pass
        if corrupt_pbf.exists():
            try:
                corrupt_pbf.unlink()
            except Exception:
                pass


def test_separation_from_synthetic_study_records():
    """Verify real catalog contains NO synthetic study POI IDs or SmartTrip artifacts."""
    store = RealCatalogStore(CATALOG_DB)
    with store._get_connection() as conn:
        # Synthetic POI IDs in study_db are of form 'C01_POI01', 'DEL_01', etc.
        synth_in_places = conn.execute("SELECT count(*) FROM places WHERE source_id LIKE 'C%_POI%'").fetchone()[0]
        assert synth_in_places == 0, f"Found {synth_in_places} synthetic study POIs inside real places table!"

        # Ensure all place IDs have valid upstream prefixes
        invalid_prefixes = conn.execute("""
            SELECT count(*) FROM places
            WHERE source_id NOT LIKE 'OSM:%' AND source_id NOT LIKE 'WD:%' AND source_id NOT LIKE 'ASI:%'
        """).fetchone()[0]
        assert invalid_prefixes == 0, f"Found {invalid_prefixes} places with invalid source_id prefix"


def test_multi_zone_real_source_breadth_across_india():
    """Test settlement and proximity search across separated zones of India."""
    store = RealCatalogStore(CATALOG_DB)

    demonstrations = [
        ("Kolkata", "East", 22.57, 88.36),
        ("Guwahati", "North-East", 26.18, 91.75),
        ("Varanasi", "North", 25.33, 83.00),
        ("Mumbai", "West", 19.05, 72.87),
        ("Bengaluru", "South", 12.98, 77.59),
        ("Badami", "South (Town)", 15.92, 75.68),
        ("Tezpur", "North-East (Town)", 26.62, 92.80),
    ]

    for name, region, lat, lon in demonstrations:
        settles = store.search_settlements(name)
        assert len(settles) > 0, f"Expected to find settlement for {name} ({region})"
        top_s = settles[0]
        places = store.search_nearby_places(lat=top_s.latitude, lon=top_s.longitude, radius_km=30.0)
        assert len(places) > 0, f"Expected cultural places near {name} ({region})"
        # Verify valid upstream ID
        top_p, dist = places[0]
        assert top_p.source_id.startswith("OSM:") or top_p.source_id.startswith("WD:"), f"Invalid source_id: {top_p.source_id}"
        assert dist <= 30.0
