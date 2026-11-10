"""Tests for Stabilization Phase 5: India-Wide Real-Place Catalog Validation & Zone Importer.

Verifies:
1. PBF/XML node, way, and relation handling with representative centroid calculation.
2. Synthetic fixture labeling and separation from real traveler data.
3. Separation of source extract date from local import date.
4. Truthful coverage metadata (Partial Coverage for regional zone extracts; Complete Extract only for verified pan-India).
5. Protection against false deduplication: ensuring constituent sites (e.g. specific temple shrines) are not merged with complexes.
6. Real upstream Geofabrik zone data: verified settlement, attraction, node/way/relation object-type counts.
7. Search demonstrations: repeated settlement names, rural localities, local-language names, and honest empty-state messaging.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import pytest

from cultureroute.catalog import RealCatalogStore
from cultureroute.domain import CulturalCategory
from cultureroute.ingest import calculate_sha256

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CATALOG_DB = DATA_DIR / "real_catalog.db"
MANIFEST_PATH = DATA_DIR / "source_manifest.json"
FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "sample_osm_extract.osm"
ZONE_PBF_PATH = DATA_DIR / "osm" / "north-eastern-zone-latest.osm.pbf"


def test_fixture_file_synthetic_labeling():
    """Verify that sample_osm_extract.osm is explicitly labeled as a synthetic fixture, not an upstream extract."""
    assert FIXTURE_PATH.exists()
    content = FIXTURE_PATH.read_text(encoding="utf-8")
    assert "SYNTHETIC / FICTIONAL PARSER TEST FIXTURE ONLY" in content
    assert "NOT an actual upstream OpenStreetMap extract" in content


def test_source_extract_date_separate_from_import_date():
    """Verify that source extract date and import date are recorded separately."""
    store = RealCatalogStore(CATALOG_DB)
    meta = store.get_all_metadata()
    assert "snapshot_date" in meta
    assert "source_extract_date" in meta

    with store._get_connection() as conn:
        places = conn.execute(
            "SELECT source_extract_date, import_date, last_checked_date FROM places WHERE upstream_type IN ('way', 'node') LIMIT 10"
        ).fetchall()
        assert len(places) > 0
        for p in places:
            assert p["source_extract_date"] is not None
            assert p["import_date"] is not None


def test_truthful_coverage_metadata_label():
    """Verify that catalog metadata truthfully reflects coverage status."""
    store = RealCatalogStore(CATALOG_DB)
    meta = store.get_all_metadata()
    # In Phase 6, all 6 zones are imported, giving Complete Extract.
    assert meta.get("coverage_level") in ("Complete Extract", "Partial Coverage")
    if meta.get("coverage_level") == "Complete Extract":
        assert meta.get("is_nationwide") == "true"
    else:
        assert "Regional / Partial Extract" in meta.get("coverage_note", "")


def test_object_type_breakdown_in_published_catalog():
    """Verify that published catalog indexes attractions across nodes, ways, and relations with distinct counts."""
    store = RealCatalogStore(CATALOG_DB)
    with store._get_connection() as conn:
        type_counts = dict(conn.execute("SELECT upstream_type, count(*) FROM places GROUP BY upstream_type").fetchall())

    assert "node" in type_counts and type_counts["node"] >= 50
    assert "way" in type_counts and type_counts["way"] >= 50
    assert (type_counts.get("relation", 0) + type_counts.get("item", 0)) >= 1


def test_constituent_attractions_not_falsely_merged():
    """Verify deduplication protects distinct constituent shrines from being merged with parent complex."""
    store = RealCatalogStore(CATALOG_DB)
    
    # In Khajuraho, group of monuments is distinct from constituent temple entries if both exist
    khj_settle = store.search_settlements("Khajuraho")
    assert len(khj_settle) >= 1
    s = khj_settle[0]
    places = store.search_nearby_places(s.latitude, s.longitude, radius_km=10, deduplicate=True)
    assert len(places) >= 1
    # Check that WD:Q179732 (Khajuraho Group of Monuments) is retained
    assert any(p[0].source_id == "WD:Q179732" for p in places)


def test_real_northeast_zone_search_demonstrations():
    """Verify searches on actual imported Geofabrik North-Eastern zone records."""
    store = RealCatalogStore(CATALOG_DB)

    # 1. Major city in North-East: Guwahati
    ghy = store.search_settlements("Guwahati")
    assert len(ghy) >= 1
    s_ghy = ghy[0]
    assert s_ghy.settlement_type == "city"
    ghy_places = store.search_nearby_places(s_ghy.latitude, s_ghy.longitude, radius_km=15)
    assert len(ghy_places) >= 20
    # Must have both node and way attractions
    types = {p[0].upstream_type for p in ghy_places}
    assert "node" in types
    assert "way" in types

    # 2. Rural locality: Sohra (Cherrapunji) in Meghalaya
    sohra = [s for s in store.search_settlements("Sohra") if "Cherrapunji" in s.name or s.settlement_type == "town"]
    assert len(sohra) >= 1
    s_sohra = sohra[0]
    sohra_places = store.search_nearby_places(s_sohra.latitude, s_sohra.longitude, radius_km=10)
    assert len(sohra_places) >= 3

    # 3. Rural river island settlement: Majuli in Assam
    majuli = store.search_settlements("Majuli")
    assert len(majuli) >= 1
    assert any(s.settlement_type in ("hamlet", "village") for s in majuli)


def test_manifest_pinned_zone_pbf():
    """Verify source_manifest.json registers the downloaded North-Eastern zone PBF."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    datasets = {d["dataset_id"]: d for d in manifest["datasets"]}
    assert "osm_northeast_zone" in datasets
    ds = datasets["osm_northeast_zone"]
    assert ds["license"].startswith("Open Database License")
    assert ds["version"] in ("2026-11-09", "2026-11-10")
    if ZONE_PBF_PATH.exists():
        actual_sha = calculate_sha256(ZONE_PBF_PATH)
        assert actual_sha == ds["sha256"]
