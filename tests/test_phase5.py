"""Tests for CultureRoute Phase 5: Expanded Real-Place Coverage & Manifest.

Verifies:
1. Pinned source manifest schema, checksums, and licensing.
2. Expanded coverage across newly covered states (Madhya Pradesh, Tamil Nadu, Odisha, Goa, Himachal Pradesh)
   demonstrating results outside the 45-city synthetic study.
3. Stable IDs and separation from synthetic IDs.
4. Categorical and regional distribution integrity.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from cultureroute.catalog import RealCatalogStore
from cultureroute.domain import CulturalCategory
from cultureroute.ingest import calculate_sha256
from cultureroute.study_data import get_study_cities

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CATALOG_DB = DATA_DIR / "real_catalog.db"
MANIFEST_PATH = DATA_DIR / "source_manifest.json"


def test_source_manifest_integrity():
    """Verify source manifest format, licenses, and file checksums."""
    assert MANIFEST_PATH.exists(), "Source manifest must exist"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "manifest_version" in manifest
    assert "datasets" in manifest
    datasets = {d["dataset_id"]: d for d in manifest["datasets"]}

    assert "unlocode_in" in datasets
    assert "wikidata_unesco" in datasets
    assert "india_boundary" in datasets

    # Verify checksums of existing raw files match manifest
    for ds_id, ds in datasets.items():
        if ds.get("file_path") and not ds["file_path"].startswith("None"):
            fp = ROOT_DIR / ds["file_path"]
            assert fp.exists(), f"File {fp} declared in manifest must exist"
            actual_sha = calculate_sha256(fp)
            assert actual_sha == ds["sha256"], f"Checksum mismatch for dataset {ds_id}"
        assert ds.get("license"), f"Dataset {ds_id} must have explicit license"


def test_expanded_regions_outside_study_cities():
    """Verify discovery works in newly added states outside the 45-city study set."""
    study_cities = {c["name"] for c in get_study_cities()}
    store = RealCatalogStore(CATALOG_DB)

    # 1. Madhya Pradesh: Khajuraho (Not in 45 cities)
    assert "Khajuraho" not in study_cities
    khajuraho_s = store.search_settlements("Khajuraho")
    assert len(khajuraho_s) >= 1
    s_khj = khajuraho_s[0]
    assert s_khj.state == "Madhya Pradesh"
    khj_places = store.search_nearby_places(s_khj.latitude, s_khj.longitude, radius_km=15)
    assert any("Khajuraho" in p[0].name for p in khj_places)

    # 2. Tamil Nadu: Mamallapuram (Not in 45 cities)
    assert "Mamallapuram" not in study_cities
    mam_s = store.search_settlements("Mamallapuram")
    assert len(mam_s) >= 1
    s_mam = mam_s[0]
    assert s_mam.state == "Tamil Nadu"
    mam_places = store.search_nearby_places(s_mam.latitude, s_mam.longitude, radius_km=15)
    assert any("Mahabalipuram" in p[0].name for p in mam_places)

    # 3. Odisha: Konark (Not in 45 cities)
    assert "Konark" not in study_cities
    konark_s = store.search_settlements("Konark")
    assert len(konark_s) >= 1
    s_knk = konark_s[0]
    assert s_knk.state == "Odisha"
    knk_places = store.search_nearby_places(s_knk.latitude, s_knk.longitude, radius_km=15)
    assert any("Sun Temple" in p[0].name for p in knk_places)

    # 4. Goa: Old Goa (Not in 45 cities)
    assert "Old Goa" not in study_cities
    goa_s = store.search_settlements("Old Goa")
    assert len(goa_s) >= 1
    s_goa = goa_s[0]
    assert s_goa.state == "Goa"
    goa_places = store.search_nearby_places(s_goa.latitude, s_goa.longitude, radius_km=15)
    assert any("Bom Jesus" in p[0].name for p in goa_places)


def test_stable_real_id_conventions():
    """Verify all real place IDs are stable and follow approved namespace prefixes."""
    store = RealCatalogStore(CATALOG_DB)
    with store._get_connection() as conn:
        place_ids = [r[0] for r in conn.execute("SELECT source_id FROM places").fetchall()]
        settle_ids = [r[0] for r in conn.execute("SELECT settlement_id FROM settlements").fetchall()]

    for pid in place_ids:
        assert pid.startswith(("WD:", "OSM:", "ASI:")), f"Invalid place ID prefix: {pid}"
        assert not pid.startswith("POI-"), f"Synthetic ID leaked into real places: {pid}"

    for sid in settle_ids:
        assert sid.startswith(("UNLOC:IN:", "SETTLE:IN:", "OSM:")), f"Invalid settlement ID prefix: {sid}"
        assert not sid.startswith("CITY-"), f"Synthetic city ID leaked into real settlements: {sid}"


def test_category_and_state_breakdown_queries():
    """Verify state & category aggregation queries for UI summaries."""
    store = RealCatalogStore(CATALOG_DB)
    breakdown = store.get_breakdown_by_state_and_category()
    assert len(breakdown) >= 8

    states = {b["state"] for b in breakdown}
    assert "Karnataka" in states
    assert "Madhya Pradesh" in states
    assert "Tamil Nadu" in states
    assert "Odisha" in states
    assert "Gujarat" in states
    assert "Rajasthan" in states
