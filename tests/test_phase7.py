"""Tests for CultureRoute Phase 7: Directed Road and Walking Routes.

Verifies:
1. DirectedRouteLeg typed data contract and units (meters, seconds, km, minutes).
2. Driving vs Walking mode constraints (walking > 25km returns UNREACHABLE_BY_MODE).
3. Walking under 25km is available.
4. Asymmetric route directional integrity (A -> B != B -> A).
5. Identity leg (A -> A) has 0 distance and 0 duration.
6. Local SQLite cache (real_route_legs) persistence and deterministic offline retrieval.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from cultureroute.routing import (
    DirectedRouteLeg,
    RouteLegStore,
    TransportMode,
    compute_directed_leg,
    MAX_WALKING_DISTANCE_KM
)

ROOT_DIR = Path(__file__).resolve().parent.parent
CATALOG_DB = ROOT_DIR / "data" / "real_catalog.db"


@pytest.fixture
def route_store():
    assert CATALOG_DB.exists(), "real_catalog.db must exist"
    return RouteLegStore(CATALOG_DB)


def test_driving_leg_between_pilot_venues(route_store):
    """Verify driving route between Badami Cave Temples and Durga Temple Aihole."""
    leg = compute_directed_leg(
        origin_id="WD:Q825236",
        origin_lat=15.9183,
        origin_lon=75.6850,
        destination_id="WD:Q3517553",
        destination_lat=16.0207,
        destination_lon=75.8819,
        mode=TransportMode.DRIVING,
        store=route_store,
        allow_network=False
    )
    assert leg.is_available is True
    assert leg.mode == TransportMode.DRIVING
    assert leg.distance_km > 25.0  # Approx 30-38 km
    assert leg.distance_meters == round(leg.distance_km * 1000, 1)
    assert leg.duration_minutes > 30.0
    assert leg.duration_seconds == round(leg.duration_minutes * 60, 1)
    assert len(leg.polyline_points) >= 2
    assert "Directed Routing Engine" in leg.source_name or "Calibrated" in leg.source_name


def test_walking_exceeding_threshold_is_unreachable(route_store):
    """Verify walking over 25 km returns explicit UNREACHABLE_BY_MODE failure."""
    leg = compute_directed_leg(
        origin_id="WD:Q825236",
        origin_lat=15.9183,
        origin_lon=75.6850,
        destination_id="WD:Q3517553",
        destination_lat=16.0207,
        destination_lon=75.8819,
        mode=TransportMode.WALKING,
        store=route_store,
        allow_network=False
    )
    assert leg.is_available is False
    assert leg.mode == TransportMode.WALKING
    assert "UNREACHABLE_BY_MODE" in leg.failure_reason
    assert "exceeds maximum realistic walking threshold" in leg.failure_reason


def test_walking_under_threshold_is_available(route_store):
    """Verify walking leg under 25 km (Aihole to Pattadakal ~13 km) is available."""
    leg = compute_directed_leg(
        origin_id="WD:Q3517553",
        origin_lat=16.0207,
        origin_lon=75.8819,
        destination_id="SETTLE:IN:PTD",
        destination_lat=15.9492,
        destination_lon=75.8169,
        mode=TransportMode.WALKING,
        store=route_store,
        allow_network=False
    )
    assert leg.is_available is True
    assert leg.distance_km < MAX_WALKING_DISTANCE_KM
    assert leg.duration_minutes > 100.0  # Approx 2.5 - 3 hours


def test_directional_asymmetry_and_identity_leg(route_store):
    """Verify identity leg (A -> A) is zero, and A -> B differs from B -> A."""
    # Identity
    ident_leg = compute_directed_leg(
        origin_id="WD:Q825236",
        origin_lat=15.9183,
        origin_lon=75.6850,
        destination_id="WD:Q825236",
        destination_lat=15.9183,
        destination_lon=75.6850,
        mode=TransportMode.DRIVING,
        store=route_store,
        allow_network=False
    )
    assert ident_leg.distance_km == 0.0
    assert ident_leg.duration_minutes == 0.0
    assert ident_leg.is_available is True

    # Asymmetry
    forward = compute_directed_leg(
        origin_id="WD:Q825236",
        origin_lat=15.9183,
        origin_lon=75.6850,
        destination_id="WD:Q3517553",
        destination_lat=16.0207,
        destination_lon=75.8819,
        mode=TransportMode.DRIVING,
        store=route_store,
        allow_network=False
    )
    reverse = compute_directed_leg(
        origin_id="WD:Q3517553",
        origin_lat=16.0207,
        origin_lon=75.8819,
        destination_id="WD:Q825236",
        destination_lat=15.9183,
        destination_lon=75.6850,
        mode=TransportMode.DRIVING,
        store=route_store,
        allow_network=False
    )
    assert forward.origin_id == reverse.destination_id
    assert forward.destination_id == reverse.origin_id
    # Asymmetric travel time due to elevation/direction
    assert forward.duration_minutes != reverse.duration_minutes


def test_sqlite_route_persistence(route_store):
    """Verify route legs stored in SQLite can be retrieved offline."""
    cached = route_store.get_cached_leg("WD:Q825236", "WD:Q3517553", TransportMode.DRIVING)
    assert cached is not None
    assert cached.distance_km > 20.0
    assert cached.is_available is True
