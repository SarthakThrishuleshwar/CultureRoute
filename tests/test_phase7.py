"""Routing contract tests with fictional coordinates and mocked provider responses."""

from datetime import datetime, timezone
import json
import sqlite3

import pytest

from cultureroute.routing import RouteLegStore, TransportMode, compute_directed_leg

A = (12.0000, 77.0000)
B = (12.0100, 77.0100)
URL = "https://configured.example.invalid"


class Reply:
    status_code = 200
    text = ""

    def __init__(self, duration=300, points=None):
        self.duration = duration
        self.points = points or [[77.0, 12.0], [77.005, 12.005], [77.01, 12.01]]

    def json(self):
        return {"code": "Ok", "routes": [{"distance": 2500, "duration": self.duration,
                                           "geometry": {"coordinates": self.points}}]}


def route(store, reverse=False, mode=TransportMode.DRIVING, **kwargs):
    origin, dest = (B, A) if reverse else (A, B)
    return compute_directed_leg("OSM:node/fictional-B" if reverse else "OSM:node/fictional-A",
        *origin, "OSM:node/fictional-A" if reverse else "OSM:node/fictional-B",
        *dest, mode, store=store, **kwargs)


def test_unconfigured_provider_is_honest(tmp_path, monkeypatch):
    monkeypatch.delenv("CULTUREROUTE_OSRM_DRIVING_URL", raising=False)
    monkeypatch.delenv("CULTUREROUTE_OSRM_URL", raising=False)
    leg = route(RouteLegStore(tmp_path / "routes.db"), allow_network=True)
    assert not leg.is_available and "ROUTING_PROVIDER_UNAVAILABLE" in leg.failure_reason


def test_directed_cache_uses_actual_provider_geometry(tmp_path, monkeypatch):
    store = RouteLegStore(tmp_path / "routes.db")
    calls = []

    def fake_get(url, **_):
        calls.append(url)
        if "77.010000,12.010000;77.000000,12.000000" in url:
            return Reply(360, [[77.01, 12.01], [77.005, 12.005], [77.0, 12.0]])
        return Reply(300)

    monkeypatch.setattr("cultureroute.routing.requests.get", fake_get)
    forward = route(store, provider_url=URL)
    reverse = route(store, reverse=True, provider_url=URL)
    assert forward.is_available and reverse.is_available
    assert forward.duration_seconds == 300 and reverse.duration_seconds == 360
    assert len(forward.polyline_points) == 3 and len(calls) == 2
    assert route(store, allow_network=False).duration_seconds == 300
    assert route(store, reverse=True, allow_network=False).duration_seconds == 360
    assert len(calls) == 2


def test_two_point_legacy_row_never_becomes_routed_leg(tmp_path):
    store = RouteLegStore(tmp_path / "routes.db")
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("""INSERT INTO real_route_legs
            (origin_id,destination_id,mode,distance_meters,duration_seconds,distance_km,
             duration_minutes,is_available,geometry_json,source_name,source_version,computed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("OSM:node/fictional-A", "OSM:node/fictional-B", "DRIVING", 2500, 300,
             2.5, 5, 1, json.dumps([A, B]), "OSRM Driving Engine (hand entered)", "unknown",
             datetime.now(timezone.utc).isoformat()))
    assert not route(store, allow_network=False).is_available


def test_walking_requires_separate_verified_profile(tmp_path, monkeypatch):
    store = RouteLegStore(tmp_path / "routes.db")
    monkeypatch.delenv("CULTUREROUTE_WALKING_PROFILE_VERIFIED", raising=False)
    assert route(store, mode=TransportMode.WALKING, provider_url=URL).failure_reason == "WALKING_PROFILE_UNVERIFIED"
    monkeypatch.setenv("CULTUREROUTE_WALKING_PROFILE_VERIFIED", "1")
    monkeypatch.setattr("cultureroute.routing.requests.get", lambda *_a, **_k: Reply())
    leg = route(store, mode=TransportMode.WALKING, provider_url=URL)
    assert leg.is_available and len(leg.polyline_points) == 3


def test_malformed_geometry_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("cultureroute.routing.requests.get", lambda *_a, **_k: Reply(points=[[77, 12], [77.01, 12.01]]))
    leg = route(RouteLegStore(tmp_path / "routes.db"), provider_url=URL)
    assert not leg.is_available and leg.failure_reason == "INVALID_ROUTE_RESPONSE"


def test_provider_timeout_creates_no_cache_row(tmp_path, monkeypatch):
    import requests
    store = RouteLegStore(tmp_path / "routes.db")
    def timeout(*_a, **_k):
        raise requests.Timeout("fictional timeout")
    monkeypatch.setattr("cultureroute.routing.requests.get", timeout)
    leg = route(store, provider_url=URL)
    assert not leg.is_available
    with sqlite3.connect(store.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM real_route_legs").fetchone()[0] == 0
