"""Comprehensive unit and integration test suite for CultureRoute Phase 2.

Tests:
1. Phase 1 study source audit checkpoints (48,728 distinct rows, 45 cities, 675 attractions, etc.).
2. Boundary validation (India bounding box and point-in-poly logic).
3. Category tag classification and strict exclusion of generic eateries.
4. Real settlement search and duplicate name disambiguation (e.g. Aurangabad MH vs BR, Udaipur RJ vs TR).
5. Real place ID validation and rejection of synthetic prefixes.
6. Unknown preservation (opening hours, entry fees, and accessibility).
7. Proximity search around real settlements outside the 45-city study set (Badami, Anegundi, Gangavathi).
8. Programmatic verification that test demonstration settlements are outside the 45-city synthetic dataset.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest

from cultureroute.study_data import verify_and_audit_study, get_study_cities
from cultureroute.boundary import is_coordinate_in_india_bbox
from cultureroute.category_rules import classify_cultural_tags
from cultureroute.catalog import RealCatalogStore, haversine_distance_km
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
)


CATALOG_DB = Path(__file__).resolve().parent.parent / "data" / "real_catalog.db"


def test_study_source_audit_preserved():
    """Verify Phase 1 synthetic audit remains 100% intact."""
    report = verify_and_audit_study()
    assert report.distinct_tables_count == 24
    assert report.distinct_rows_count == 48728
    assert report.india_cities_count == 45
    assert report.india_attractions_count == 675
    assert report.study_trips_count == 411
    assert report.matched_interactions_count == 6850
    assert report.selected_stops_count == 3191


def test_boundary_validation():
    """Test India coordinate bounding box."""
    # Delhi, Bengaluru, Badami, Anegundi
    assert is_coordinate_in_india_bbox(28.6139, 77.2090) is True
    assert is_coordinate_in_india_bbox(12.9716, 77.5946) is True
    assert is_coordinate_in_india_bbox(15.9189, 75.6842) is True
    assert is_coordinate_in_india_bbox(15.3524, 76.4952) is True

    # London, New York, Tokyo
    assert is_coordinate_in_india_bbox(51.5074, -0.1278) is False
    assert is_coordinate_in_india_bbox(40.7128, -74.0060) is False
    assert is_coordinate_in_india_bbox(35.6762, 139.6503) is False


def test_category_tag_classification():
    """Verify that cultural tags are classified and generic modern eateries are rejected."""
    # Defensible Heritage
    cat, subcat = classify_cultural_tags({"historic": "monument", "name": "Historic Pillar"})
    assert cat == CulturalCategory.HERITAGE
    assert subcat == "monument"

    # Defensible Museum
    cat, subcat = classify_cultural_tags({"tourism": "museum", "name": "Art Gallery"})
    assert cat == CulturalCategory.MUSEUM

    # Defensible Religious
    cat, subcat = classify_cultural_tags({"amenity": "place_of_worship", "religion": "hindu"})
    assert cat == CulturalCategory.RELIGIOUS

    # Defensible Traditional Food Market
    cat, subcat = classify_cultural_tags({"amenity": "marketplace", "name": "Heritage Bazaar"})
    assert cat == CulturalCategory.FOOD

    # STRICT EXCLUSIONS: Generic fast food or modern restaurant
    assert classify_cultural_tags({"amenity": "fast_food", "name": "Burger Joint"}) is None
    assert classify_cultural_tags({"amenity": "restaurant", "name": "City Cafe & Bistro"}) is None


def test_real_id_separation_and_synthetic_rejection():
    """Verify that any synthetic ID or prefix is rejected from RealPlaceRecord."""
    # Synthetic study prefix 'poi_'
    with pytest.raises(ValueError, match="Synthetic prefix 'poi_' prohibited"):
        RealPlaceRecord(
            source_id="poi_7f6561ec",
            upstream_type="node",
            upstream_id="123",
            name="Synthetic Test",
            latitude=15.0,
            longitude=75.0,
            state="Karnataka",
            settlement_type="town",
            cultural_category=CulturalCategory.HERITAGE,
            source_url="https://example.com",
            source_extract_date=date(2026, 10, 15),
            import_date=date(2026, 11, 9),
            last_checked_date=date(2026, 11, 9),
        )

    # Valid external real ID
    record = RealPlaceRecord(
        source_id="OSM:node/34829104",
        upstream_type="node",
        upstream_id="34829104",
        name="Badami Cave Temples",
        latitude=15.9189,
        longitude=75.6842,
        state="Karnataka",
        district="Bagalkot",
        settlement_type="town",
        cultural_category=CulturalCategory.HERITAGE,
        source_url="https://www.openstreetmap.org/node/34829104",
        source_extract_date=date(2026, 10, 15),
        import_date=date(2026, 11, 9),
        last_checked_date=date(2026, 11, 9),
    )
    assert record.source_id == "OSM:node/34829104"


def test_outside_study_search_demonstrations():
    """Verify searches for two real locations outside the 45-city study set.
    
    Demonstration 1: Badami, Karnataka (Historic town with ancient cave temples)
    Demonstration 2: Anegundi, Karnataka (Rural historic village across Tungabhadra)
    """
    study_cities = {c["name"] for c in get_study_cities()}
    assert "Badami" not in study_cities, "Badami must be outside the 45-city synthetic dataset"
    assert "Anegundi" not in study_cities, "Anegundi must be outside the 45-city synthetic dataset"

    store = RealCatalogStore(CATALOG_DB)

    # 1. Badami demonstration
    badami_results = store.search_settlements("Badami")
    assert len(badami_results) >= 1
    badami = badami_results[0]
    assert badami.name == "Badami"
    assert badami.state == "Karnataka"

    nearby_badami = store.search_nearby_places(badami.latitude, badami.longitude, radius_km=25.0)
    assert len(nearby_badami) >= 2
    place_names = [p.name for p, _ in nearby_badami]
    assert "Badami Cave Temples" in place_names
    assert any("Pattadakal" in name for name in place_names)

    # Check Badami Cave Temples details (audited in Phase 3 as unverified hours/fees -> UNKNOWN)
    badami_caves = next(p for p, _ in nearby_badami if p.name == "Badami Cave Temples")
    assert badami_caves.source_id == "WD:Q825236"
    assert badami_caves.cultural_category == CulturalCategory.HERITAGE
    assert badami_caves.opening_hours.status == VerificationStatus.UNKNOWN
    assert badami_caves.entry_fee.status == FeeStatus.UNKNOWN

    # 2. Anegundi demonstration (Rural locality)
    anegundi_results = store.search_settlements("Anegundi")
    assert len(anegundi_results) == 1
    anegundi = anegundi_results[0]
    assert anegundi.settlement_type == "village"


    nearby_anegundi = store.search_nearby_places(anegundi.latitude, anegundi.longitude, radius_km=10.0)
    assert len(nearby_anegundi) >= 1
    hampi = nearby_anegundi[0][0]
    assert hampi.source_id == "WD:Q26732"
    assert "Hampi" in hampi.name
    assert hampi.cultural_category == CulturalCategory.HERITAGE

    # Verify honest UNKNOWN status preservation in rural / audited places
    assert hampi.opening_hours.status == VerificationStatus.UNKNOWN
    assert hampi.entry_fee.status == FeeStatus.UNKNOWN
    assert hampi.accessibility.status == AccessibilityStatus.UNKNOWN


def test_settlement_disambiguation():
    """Verify that duplicate names across different states are returned for disambiguation."""
    store = RealCatalogStore(CATALOG_DB)
    # Search Aurangabad (Maharashtra vs Bihar)
    results = store.search_settlements("Aurangabad")
    states = {s.state for s in results}
    assert "Maharashtra" in states
    assert "Bihar" in states

    # Search Udaipur (Rajasthan vs Tripura)
    results_udr = store.search_settlements("Udaipur")
    states_udr = {s.state for s in results_udr}
    assert "Rajasthan" in states_udr
    assert "Tripura" in states_udr


def test_empty_search_results():
    """Verify honest empty result state when no cultural places exist in tight proximity."""
    store = RealCatalogStore(CATALOG_DB)
    # Gangavathi within 3 km has 0 cultural places in the catalog
    gangavathi_results = store.search_settlements("Gangavathi")
    assert len(gangavathi_results) >= 1
    g = gangavathi_results[0]

    nearby_tight = store.search_nearby_places(g.latitude, g.longitude, radius_km=3.0)
    assert len(nearby_tight) == 0, "Expected honest empty result within 3km"

    # Expanding to 15km finds Anegundi attractions
    nearby_wider = store.search_nearby_places(g.latitude, g.longitude, radius_km=15.0)
    assert len(nearby_wider) >= 1
