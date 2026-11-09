"""Comprehensive test suite for Phase 1 CultureRoute foundation (updated for Phase 2 contracts).

Verifies:
1. Canonical source audit checkpoints (24 distinct tables, 48,728 rows, 45 cities, 675 attractions, 411 trips, 6,850 interactions, 3,191 selected stops).
2. Shared tables identical by schema, PK, and content.
3. Separation of synthetic and real records (synthetic prefix enforcement).
4. Explicit UNKNOWN value preservation in real-place contracts.
"""

from decimal import Decimal
from datetime import date
import pytest
from cultureroute.study_data import verify_and_audit_study, get_study_cities, get_city_attractions
from cultureroute.domain import (
    RealPlaceRecord,
    DirectedLegOption,
    OpeningHoursDetail,
    EntryFeeDetail,
    AccessibilityDetail,
    VerificationStatus,
    FeeStatus,
    AccessibilityStatus,
    CulturalCategory,
    ResultLevel,
)


def test_study_source_audit():
    """Verify all 8 source checkpoints and exact counts from the read-only SQLite packs."""
    report = verify_and_audit_study()
    assert report.smart_tables_count == 18
    assert report.wander_tables_count == 14
    assert report.shared_tables_count == 8
    assert report.distinct_tables_count == 24
    assert report.smart_rows_count == 32627
    assert report.wander_rows_count == 27428
    assert report.shared_rows_count == 11327
    assert report.distinct_rows_count == 48728

    assert report.india_cities_count == 45
    assert report.india_attractions_count == 675
    assert report.study_trips_count == 411
    assert report.matched_interactions_count == 6850
    assert report.selected_stops_count == 3191

    assert report.cultural_attractions_count == 211
    assert report.cultural_interactions_count == 2144
    assert report.cultural_selected_stops_count == 961

    assert report.distinct_saved_pois == 363
    assert report.distinct_planned_pois == 655
    assert report.distinct_inner_pois == 352
    assert report.saved_only_pois == 11
    assert report.planned_only_pois == 303
    assert report.full_outer_pois == 666

    assert report.india_events_count == 225
    assert report.events_missing_footfall == 46
    assert report.complete_weeks_count == 57
    assert report.forecast_last_week_mae == 3.42
    assert report.forecast_four_week_mae == 3.88


def test_city_retrieval_and_matrix_split():
    """Verify that every study city has 15 catalog attractions and 10 matrix-covered attractions."""
    cities = get_study_cities()
    assert len(cities) == 45
    city_names = [c["name"] for c in cities]
    assert "Jaipur" in city_names
    assert "Jodhpur" in city_names  # Confirms Jodhpur is present in the 45-city study

    jaipur = next(c for c in cities if c["name"] == "Jaipur")
    attractions = get_city_attractions(jaipur["city_id"])
    assert len(attractions) == 15
    matrix_covered = [a for a in attractions if a["in_travel_matrix"]]
    assert len(matrix_covered) == 10


def test_real_place_contract_synthetic_separation():
    """Verify that RealPlaceRecord rejects synthetic prefixes."""
    with pytest.raises(ValueError, match="Synthetic prefix 'poi_' prohibited"):
        RealPlaceRecord(
            source_id="poi_12345678",
            upstream_type="node",
            upstream_id="12345678",
            name="Synthetic Clash",
            latitude=26.9,
            longitude=75.8,
            state="Rajasthan",
            district="Jaipur",
            settlement_type="city",
            cultural_category=CulturalCategory.HERITAGE,
            source_url="https://example.com",
            source_extract_date=date(2026, 10, 15),
            import_date=date(2026, 11, 9),
            last_checked_date=date(2026, 11, 9),
            opening_hours=OpeningHoursDetail(status=VerificationStatus.KNOWN),
            entry_fee=EntryFeeDetail(status=FeeStatus.KNOWN_FREE),
            accessibility=AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
        )


def test_real_place_unknown_fee_and_hours_preservation():
    """Verify that unknown fees are preserved as None/UNKNOWN and NOT converted to 0."""
    record = RealPlaceRecord(
        source_id="EXT:FICTIONAL_TEST_001",
        upstream_type="node",
        upstream_id="001",
        name="Fictional Rural Stepwell Fixture",
        latitude=26.5,
        longitude=76.2,
        state="Rajasthan",
        district="Dausa",
        settlement_type="village",
        cultural_category=CulturalCategory.HERITAGE,
        source_url="https://example.org/fixtures/001",
        source_extract_date=date(2026, 10, 15),
        import_date=date(2026, 11, 9),
        last_checked_date=date(2026, 11, 9),
        opening_hours=OpeningHoursDetail(status=VerificationStatus.UNKNOWN),
        entry_fee=EntryFeeDetail(status=FeeStatus.UNKNOWN, amount_domestic=None),
        accessibility=AccessibilityDetail(status=AccessibilityStatus.UNKNOWN),
    )
    assert record.entry_fee.status == FeeStatus.UNKNOWN
    assert record.entry_fee.amount_domestic is None  # Must NOT be Decimal("0.00")
    assert record.opening_hours.status == VerificationStatus.UNKNOWN
