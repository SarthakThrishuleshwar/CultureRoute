"""Tests for Stabilization Phase 4: India-Wide Real-Place Import, Deduplication, and Fixture Validation.

Verifies:
1. Canonical deduplication for Khajuraho and Konark (preserving upstream raw IDs while presenting one canonical venue).
2. OSM streaming parser with real OSM XML fixture (settlements, cultural attractions, excluded amenities, boundary filtering).
3. Search disambiguation and alternate/multilingual name matching.
4. Correct unindexed search state semantics ("not found in this index", not proof of non-existence).
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import pytest

from cultureroute.boundary import IndiaBoundaryValidator
from cultureroute.catalog import RealCatalogStore
from cultureroute.ingest import OsmStreamingImporter, run_streaming_import

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CATALOG_DB = DATA_DIR / "real_catalog.db"
BOUNDARY_GEOJSON = DATA_DIR / "india_boundary.geojson"
OSM_FIXTURE = ROOT_DIR / "tests" / "fixtures" / "sample_osm_extract.osm"


def test_khajuraho_and_konark_canonical_deduplication():
    """Verify that search_nearby_places collapses duplicate venues into a canonical entry.
    
    Both raw records (e.g. WD:Q179732 & WD:Q167298 for Khajuraho; WD:Q219985 & WD:Q752091 for Konark)
    must remain stored in the database, but user search returns only one canonical place.
    """
    store = RealCatalogStore(CATALOG_DB)

    # 1. Verify underlying database has both raw records for Khajuraho
    with store._get_connection() as conn:
        khj_raw = conn.execute(
            "SELECT source_id, name, latitude, longitude FROM places WHERE name LIKE '%Khajuraho%'"
        ).fetchall()
        assert len(khj_raw) >= 2, f"Expected at least 2 raw Khajuraho records, found {len(khj_raw)}"
        khj_ids = {r[0] for r in khj_raw}
        assert "WD:Q179732" in khj_ids
        assert "WD:Q167298" in khj_ids

    # 2. Search nearby Khajuraho settlement with deduplication (default)
    khj_settlements = store.search_settlements("Khajuraho")
    assert len(khj_settlements) >= 1
    s_khj = khj_settlements[0]
    
    deduped_places = store.search_nearby_places(s_khj.latitude, s_khj.longitude, radius_km=15, deduplicate=True)
    khj_matches = [p[0] for p in deduped_places if "khajuraho group" in p[0].name.lower()]
    assert len(khj_matches) == 1, f"Expected exactly 1 canonical Khajuraho venue, found {len(khj_matches)}"
    assert khj_matches[0].source_id == "WD:Q179732", "Expected WD:Q179732 to be selected as canonical"

    # 3. Verify Konark raw records and canonical search
    with store._get_connection() as conn:
        knk_raw = conn.execute(
            "SELECT source_id, name, latitude, longitude FROM places WHERE name LIKE '%Konark%' or name LIKE '%Sun Temple%'"
        ).fetchall()
        assert len(knk_raw) >= 2, f"Expected at least 2 raw Konark records, found {len(knk_raw)}"
        knk_ids = {r[0] for r in knk_raw}
        assert "WD:Q219985" in knk_ids
        assert "WD:Q752091" in knk_ids

    knk_settlements = store.search_settlements("Konark")
    assert len(knk_settlements) >= 1
    s_knk = knk_settlements[0]

    deduped_knk = store.search_nearby_places(s_knk.latitude, s_knk.longitude, radius_km=15, deduplicate=True)
    knk_matches = [p[0] for p in deduped_knk if "sun temple" in p[0].name.lower()]
    assert len(knk_matches) == 1, f"Expected exactly 1 canonical Konark Sun Temple venue, found {len(knk_matches)}"
    assert knk_matches[0].source_id == "WD:Q219985", "Expected WD:Q219985 to be selected as canonical"


def test_osm_streaming_importer_on_real_fixture():
    """Verify that OsmStreamingImporter parses OSM primitives, validates boundaries, and filters correctly."""
    assert OSM_FIXTURE.exists(), "OSM test fixture must exist"
    validator = IndiaBoundaryValidator(BOUNDARY_GEOJSON)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db = Path(tmp.name)

    try:
        # Run streaming import on the fixture
        stats = run_streaming_import(
            output_db=test_db,
            boundary_geojson=BOUNDARY_GEOJSON,
            osm_pbf=OSM_FIXTURE,
            unlocode_csv=None,
            unesco_json=None,
        )

        assert stats["settlements_count"] >= 1
        assert stats["places_count"] >= 3
        # Extraterritorial node (Foreign City) must be rejected
        assert stats["osm_stats"]["rejected_boundary"]["nodes"] >= 1

        store = RealCatalogStore(test_db)

        # 1. Verify Synthetic Test Town settlement imported
        settlements = store.search_settlements("Synthetic Test Town")
        assert len(settlements) >= 1
        s = settlements[0]
        assert s.name == "Synthetic Test Town"
        assert s.settlement_type == "town"
        assert "kn" in s.local_names
        assert s.local_names["kn"] == "ಟೆಸ್ಟ್ ಪಟ್ಟಣ"

        # 2. Verify cultural places imported across nodes, ways, and relations
        nearby = store.search_nearby_places(s.latitude, s.longitude, radius_km=5)
        names = [p[0].name for p in nearby]
        assert any("Synthetic Test Temple" in n for n in names)
        assert any("Synthetic Test Palace" in n for n in names)
        assert any("Synthetic Test Fort Wall" in n for n in names)
        assert any("Synthetic Test Heritage Complex" in n for n in names)

        # 3. Verify excluded generic amenity (Fast Food) was NOT imported
        assert not any("Fast Food" in n for n in names)

        # 4. Verify rejected extraterritorial place was NOT imported
        with store._get_connection() as conn:
            foreign_rows = conn.execute("SELECT * FROM settlements WHERE name LIKE '%Foreign City%'").fetchall()
            assert len(foreign_rows) == 0
    finally:
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass


def test_multilingual_settlement_search():
    """Verify that search_settlements matches local-language names (e.g. Kannada, Hindi)."""
    store = RealCatalogStore(CATALOG_DB)

    # Search for Badami by Kannada name: ಬಾದಾಮಿ (\u0cac\u0cbe\u0ca6\u0cbe\u0cae\u0cbf)
    badami_results = store.search_settlements("\u0cac\u0cbe\u0ca6\u0cbe\u0cae\u0cbf")
    assert len(badami_results) >= 1
    assert any(s.name == "Badami" for s in badami_results)

    # Search for Pattadakal by Kannada name: ಪಟ್ಟದಕಲ್ಲು (\u0caa\u0c9f\u0ccd\u0c9f\u0ca6\u0c95\u0cb2\u0ccd\u0cb2\u0cc1)
    ptd_results = store.search_settlements("\u0caa\u0c9f\u0ccd\u0c9f\u0ca6\u0c95\u0cb2\u0ccd\u0cb2\u0cc1")
    assert len(ptd_results) >= 1
    assert any(s.name == "Pattadakal" for s in ptd_results)

    # Search for Khajuraho by Hindi name: खजुराहो (\u0916\u091c\u0941\u0930\u093e\u0939\u094b)
    khj_results = store.search_settlements("\u0916\u091c\u0941\u0930\u093e\u0939\u094b")
    assert len(khj_results) >= 1
    assert any(s.name == "Khajuraho" for s in khj_results)


def test_unindexed_search_wording_semantics():
    """Verify that catalog search clarifies unindexed state vs non-existence."""
    store = RealCatalogStore(CATALOG_DB)
    results = store.search_settlements("NonExistentAtlantisXYZ")
    assert len(results) == 0
    # No matches simply returns an empty list, allowing UI to present:
    # "not found in this index" with explicit clarification that it is unindexed, not proven nonexistent.
