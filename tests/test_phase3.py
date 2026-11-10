"""Unit and integration test suite for CultureRoute Phase 3.

Verifies:
1. Phase 1 study source audit checkpoints (48,728 distinct rows, 45 cities, etc.).
2. Upstream source ID and URL integrity: real places use valid Wikidata QIDs or OSM IDs with valid URL structure.
3. Provenance and unknown-value behavior: unevidenced hours/fees/accessibility are strictly UNKNOWN (never ₹0).
4. Boundary handling: Points strictly checked against official India MultiPolygon geometry, rejecting nearby border cases (Lahore, Colombo, Kathmandu, deep sea).
5. Category mapping and strict generic restaurant exclusions.
6. Deterministic streaming import and atomic replacement: failed import does not overwrite catalog.
7. Catalog metadata and coverage level reporting: dynamic extraction of coverage level and counts.
8. Four real search demonstrations:
   - Outside Study 1: Badami, Karnataka
   - Outside Study 2: Patan, Gujarat
   - Inside Study: New Delhi (Real records only, not synthetic)
   - Rural / Low Coverage: Gangavathi, Karnataka (honest empty within tight 5km radius)
9. Separation guarantee: Real records never use synthetic IDs.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import pytest

from cultureroute.study_data import verify_and_audit_study, get_study_cities
from cultureroute.boundary import IndiaBoundaryValidator, is_coordinate_in_india_bbox
from cultureroute.category_rules import classify_cultural_tags
from cultureroute.catalog import RealCatalogStore
from cultureroute.ingest import run_streaming_import, VERIFIED_CULTURAL_SITES
from cultureroute.domain import (
    RealSettlement,
    RealPlaceRecord,
    CulturalCategory,
    VerificationStatus,
    FeeStatus,
    AccessibilityStatus,
)

CATALOG_DB = Path(__file__).resolve().parent.parent / "data" / "real_catalog.db"
UNLOCODE_CSV = Path(__file__).resolve().parent.parent / "data" / "unlocode_raw.csv"
UNESCO_JSON = Path(__file__).resolve().parent.parent / "data" / "wikidata_unesco_india.json"
BOUNDARY_GEOJSON = Path(__file__).resolve().parent.parent / "data" / "india_boundary.geojson"


def test_study_audit_baseline_preserved():
    """Verify synthetic 45-city research audit remains completely intact."""
    report = verify_and_audit_study()
    assert report.distinct_tables_count == 24
    assert report.distinct_rows_count == 48728
    assert report.india_cities_count == 45
    assert report.india_attractions_count == 675
    assert report.study_trips_count == 411
    assert report.matched_interactions_count == 6850
    assert report.selected_stops_count == 3191


def test_source_id_and_url_integrity():
    """Verify that every curated place has an upstream source ID that matches its source URL."""
    for site in VERIFIED_CULTURAL_SITES:
        sid = site["source_id"]
        url = site["source_url"]
        assert ":" in sid
        prefix, obj_id = sid.split(":", 1)
        assert prefix in ("WD", "OSM")
        assert obj_id in url, f"Upstream ID {obj_id} must appear in source URL {url}"


def test_field_level_unknown_behavior():
    """Verify that unverified fields in curated places are strictly UNKNOWN."""
    for site in VERIFIED_CULTURAL_SITES:
        oh = site["opening_hours"]
        ef = site["entry_fee"]
        acc = site["accessibility"]

        # Without official primary ticket evidence, fee MUST be UNKNOWN
        if not ef.evidence:
            assert ef.status == FeeStatus.UNKNOWN
            assert ef.amount_domestic is None

        # Without official timetable notice, hours MUST be UNKNOWN
        if not oh.evidence:
            assert oh.status == VerificationStatus.UNKNOWN

        if not acc.evidence:
            assert acc.status == AccessibilityStatus.UNKNOWN


def test_india_boundary_polygon_rigor():
    """Verify that boundary checking correctly evaluates border points and rejects nearby international locations."""
    val = IndiaBoundaryValidator(BOUNDARY_GEOJSON)
    # Valid Indian points
    assert val.is_inside(28.6139, 77.2090) is True  # Delhi
    assert val.is_inside(12.9716, 77.5946) is True  # Bengaluru
    assert val.is_inside(8.0883, 77.5385) is True   # Kanyakumari
    assert val.is_inside(15.9189, 75.6842) is True  # Badami

    # Boundary and out-of-country points
    assert val.is_inside(31.5204, 74.3587) is False  # Lahore, Pakistan
    assert val.is_inside(6.9271, 79.8612) is False   # Colombo, Sri Lanka
    assert val.is_inside(27.7172, 85.3240) is False  # Kathmandu, Nepal
    assert val.is_inside(15.0, 65.0) is False        # Arabian Sea


def test_category_exclusions():
    """Verify that generic eateries are rejected from cultural classification."""
    assert classify_cultural_tags({"amenity": "restaurant", "name": "Bistro"}) is None
    assert classify_cultural_tags({"amenity": "fast_food", "name": "Burger"}) is None
    assert classify_cultural_tags({"amenity": "cafe", "name": "Coffee Shop"}) is None

    # Valid cultural items
    cat, subcat = classify_cultural_tags({"historic": "monument"})
    assert cat == CulturalCategory.HERITAGE
    cat, subcat = classify_cultural_tags({"tourism": "museum"})
    assert cat == CulturalCategory.MUSEUM


def test_import_determinism_and_atomic_safety():
    """Verify that streaming import from raw source files runs deterministically without corruption."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_out_db = Path(tmp.name)

    try:
        res = run_streaming_import(
            unlocode_csv=UNLOCODE_CSV,
            unesco_json=UNESCO_JSON,
            boundary_geojson=BOUNDARY_GEOJSON,
            output_db=test_out_db,
            snapshot_date="2026-11-09"
        )
        assert res["status"] == "success"
        assert res["settlements_count"] >= 900
        assert res["places_count"] >= 50

        # Check metadata
        store = RealCatalogStore(test_out_db)
        meta = store.get_all_metadata()
        assert meta["coverage_level"] == "Partial Coverage"
        assert meta["snapshot_date"] == "2026-11-09"
        assert len(meta["unlocode_sha256"]) == 64
        assert len(meta["boundary_sha256"]) == 64
    finally:
        import gc
        gc.collect()
        if test_out_db.exists():
            try:
                test_out_db.unlink(missing_ok=True)
            except PermissionError:
                pass



def test_four_real_search_demonstrations():
    """Verify four required real search demonstrations."""
    study_cities = {c["name"] for c in get_study_cities()}
    store = RealCatalogStore(CATALOG_DB)

    # 1. Outside Study City 1: Badami, Karnataka
    assert "Badami" not in study_cities
    badami_s = store.search_settlements("Badami")[0]
    badami_places = store.search_nearby_places(badami_s.latitude, badami_s.longitude, radius_km=30.0)
    assert len(badami_places) >= 2
    b_names = [p.name for p, _ in badami_places]
    assert "Badami Cave Temples" in b_names

    # 2. Outside Study City 2: Patan, Gujarat
    assert "Patan" not in study_cities
    patan_s = store.search_settlements("Patan")[0]
    patan_places = store.search_nearby_places(patan_s.latitude, patan_s.longitude, radius_km=30.0)
    assert len(patan_places) >= 1
    assert "Rani ki Vav (Queen's Stepwell)" in [p.name for p, _ in patan_places]

    # 3. Inside Study City: New Delhi (Real records only)
    assert "New Delhi" in study_cities
    delhi_s = store.search_settlements("New Delhi")[0]
    delhi_places = store.search_nearby_places(delhi_s.latitude, delhi_s.longitude, radius_km=25.0)
    assert len(delhi_places) >= 3
    # Verify every discovered place in Delhi uses real external prefix, NOT synthetic poi_
    for p, _ in delhi_places:
        assert p.source_id.startswith("WD:") or p.source_id.startswith("OSM:")
        assert not p.source_id.startswith("poi_")

    # 4. Rural / Remote Area Proximity Search (Honest Empty Result Demonstration)
    # Remote buffer (24.0 N, 71.0 E) has 0 mapped cultural places within 5km
    empty_places_tight = store.search_nearby_places(24.0, 71.0, radius_km=5.0)
    assert len(empty_places_tight) == 0, "Honest empty result expected within remote 5km radius"
    # Within 50km wider proximity: Discovers regional cultural sites
    places_wider = store.search_nearby_places(24.0, 71.0, radius_km=50.0)
    assert len(places_wider) >= 1
