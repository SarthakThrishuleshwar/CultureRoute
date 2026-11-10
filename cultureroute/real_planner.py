"""Conservative real-place day plans built from catalog, evidence and routed legs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import itertools
from pathlib import Path
from typing import List, Optional

from cultureroute.catalog import RealCatalogStore
from cultureroute.evidence import VenueEvidenceStore, FieldEvidenceStatus
from cultureroute.routing import (DEFAULT_ROUTES_DB, RouteLegStore, TransportMode,
                                  compute_directed_leg, configured_backend)


@dataclass(frozen=True)
class RealPlanStop:
    stop_index: int
    poi_id: str
    name: str
    category: str
    is_cultural: bool
    arrival_time: str
    visit_start_time: str
    visit_end_time: str
    duration_minutes: int
    entry_fee: Optional[Decimal]
    fee_status: str
    accessibility: str
    hours_status: str
    latitude: float
    longitude: float
    is_duration_assumption: bool
    evidence_url: Optional[str] = None


@dataclass(frozen=True)
class RealPlanLeg:
    leg_index: int
    origin_id: str
    origin_name: str
    destination_id: str
    destination_name: str
    mode: str
    travel_minutes: int
    distance_km: float
    source: str
    polyline_points: list[tuple[float, float]]
    fare_inr: Optional[Decimal] = None


@dataclass(frozen=True)
class RealDayPlan:
    plan_id: str
    objective: str
    namespace: str
    city_or_region: str
    visit_date: str
    start_time: str
    elapsed_minutes: int
    elapsed_formatted: str
    cultural_stops_count: int
    total_stops_count: int
    entry_cost_inr: Optional[Decimal]
    travel_cost_inr: Optional[Decimal]
    total_cost_inr: Optional[Decimal]
    estimated_carbon_kg: None
    stops: List[RealPlanStop]
    legs: List[RealPlanLeg]
    result_level: str
    reasons: List[str] = field(default_factory=list)
    has_unknown_costs: bool = True
    transport_mode: str = "DRIVING"
    route_geometry_available: bool = True
    known_admission_subtotal_inr: Decimal = Decimal("0")


def _minute(text: str) -> Optional[int]:
    try:
        hh, mm = (int(x) for x in text.split(":"))
        return hh * 60 + mm if 0 <= hh < 24 and 0 <= mm < 60 else None
    except (ValueError, AttributeError):
        return None


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _elapsed(minutes: int) -> str:
    return f"{minutes // 60}h {minutes % 60:02d}m"


def _real_id(source_id: str) -> bool:
    return source_id.startswith(("OSM:", "WD:", "ASI:"))


def plan_real_place_day(*, catalog_db: Path, evidence_db: Path,
                        routes_db: Path = DEFAULT_ROUTES_DB,
                        selected_place_ids: Optional[List[str]] = None,
                        settlement_id: Optional[str] = None,
                        visit_date: Optional[date] = None, start_time: str = "09:00",
                        max_duration_hours: float = 8, target_stops: int = 2,
                        transport_mode: TransportMode = TransportMode.DRIVING,
                        step_free_required: bool = False, visitor_scope: str = "INDIAN_ADULT",
                        user_duration_minutes: int = 60, round_trip: bool = False,
                        allow_network: bool = True, budget_inr: Optional[float] = None,
                        radius_km: float = 15) -> dict:
    """Return a routed conditional plan or a specific infeasibility reason.

    Unknown venue facts never become zero costs or invented opening windows.
    A timetable with unknown hours is illustrative and classified DISCOVERY-ONLY.
    """
    fail = lambda reason: {"fastest": None, "most_cultural": None, "infeasible_reason": reason}
    day = visit_date or date.today()
    start = _minute(start_time)
    if start is None or max_duration_hours <= 0 or not 1 <= target_stops <= 5 or not 15 <= user_duration_minutes <= 240:
        return fail("Invalid start time, duration, stop count or traveler visit-duration input.")
    if budget_inr is not None and budget_inr < 0:
        return fail("Budget cannot be negative.")
    if not configured_backend(transport_mode) and allow_network:
        return fail(f"No configured {transport_mode.value.lower()} routing backend. Set the matching CULTUREROUTE_OSRM_*_URL.")

    catalog = RealCatalogStore(catalog_db)
    evidence = VenueEvidenceStore(evidence_db)
    routes = RouteLegStore(routes_db)
    hub = catalog.get_settlement_by_id(settlement_id) if settlement_id else None
    if settlement_id and hub is None:
        return fail("Settlement ID is absent from the real catalog.")
    candidates = []
    if selected_place_ids:
        for sid in dict.fromkeys(selected_place_ids):
            if not _real_id(sid):
                raise ValueError(f"Synthetic or unsupported place ID rejected: {sid}")
            place = catalog.get_place_by_id(sid)
            if place is None:
                return fail(f"Real place ID is absent from the catalog: {sid}")
            candidates.append(place)
    elif hub:
        nearby = catalog.search_nearby_places(hub.latitude, hub.longitude, radius_km=radius_km)
        candidates = [p for p, _ in nearby[:6]]
    else:
        return fail("Choose a real settlement or at least one real place.")
    if len(candidates) < target_stops:
        return fail(f"Only {len(candidates)} indexed cultural places are available for {target_stops} requested stops.")

    details = {}
    excluded = []
    for place in candidates:
        sid = place.source_id
        fields = {name: evidence.resolve_field(sid, name, day, visitor_scope)
                  for name in ("opening_hours", "entry_fee", "step_free_access", "operating_status", "typical_duration")}
        status = fields["operating_status"]
        hours = fields["opening_hours"]
        access = fields["step_free_access"]
        if status.status == FieldEvidenceStatus.VERIFIED and status.value and status.value.get("status") == "CLOSED":
            excluded.append(f"{place.name} has a documented closure for {day}.")
            continue
        if hours.status in (FieldEvidenceStatus.VERIFIED, FieldEvidenceStatus.PROVISIONAL) and hours.value and day.strftime("%A") in hours.value.get("closed_days", []):
            excluded.append(f"{place.name} is documented closed on {day.strftime('%A')}.")
            continue
        if step_free_required and not (access.status == FieldEvidenceStatus.VERIFIED and access.value and
                                       access.value.get("is_accessible") is True):
            excluded.append(f"{place.name} lacks verified step-free access.")
            continue
        details[sid] = fields
    candidates = [p for p in candidates if p.source_id in details]
    if len(candidates) < target_stops:
        return fail("Not enough eligible venues. " + " ".join(excluded[:3]))

    max_minutes = round(max_duration_hours * 60)
    route_errors = []
    plans = []
    for order in itertools.permutations(candidates, target_stops):
        first = order[0]
        origin_id = hub.settlement_id if hub else first.source_id
        origin_name = hub.name if hub else first.name
        origin_lat = hub.latitude if hub else first.latitude
        origin_lon = hub.longitude if hub else first.longitude
        current = start
        stops = []
        legs = []
        known_admission = Decimal("0")
        unknown_fee = False
        unknown_hours = False
        unknown_status = False
        unknown_access = False
        assumption_duration = False
        feasible = True
        for idx, place in enumerate(order):
            if origin_id != place.source_id:
                route = compute_directed_leg(origin_id, origin_lat, origin_lon, place.source_id,
                                             place.latitude, place.longitude, transport_mode, routes,
                                             allow_network=allow_network)
                if not route.is_available:
                    route_errors.append(route.failure_reason or "Unreachable route")
                    feasible = False
                    break
                current += round(route.duration_minutes)
                legs.append(RealPlanLeg(len(legs) + 1, origin_id, origin_name, place.source_id,
                                        place.name, transport_mode.value, round(route.duration_minutes),
                                        route.distance_km, route.source_name, route.polyline_points))
            fields = details[place.source_id]
            hours, fee, status, access, duration = (fields[n] for n in
                ("opening_hours", "entry_fee", "operating_status", "step_free_access", "typical_duration"))
            arrival = current
            open_min = close_min = None
            if hours.status == FieldEvidenceStatus.VERIFIED and hours.value:
                open_min = _minute(hours.value.get("opens_at"))
                close_min = _minute(hours.value.get("closes_at"))
            if open_min is None or close_min is None:
                unknown_hours = True
            elif current < open_min:
                current = open_min
            dwell = user_duration_minutes
            is_assumption = True
            if duration.status == FieldEvidenceStatus.VERIFIED and duration.value:
                official = duration.value.get("duration_minutes")
                if isinstance(official, int) and official > 0:
                    dwell = official
                    is_assumption = False
            assumption_duration |= is_assumption
            if close_min is not None and current + dwell > close_min:
                feasible = False
                break
            if fee.status == FieldEvidenceStatus.VERIFIED and fee.value and fee.value.get("amount") is not None:
                amount = Decimal(str(fee.value["amount"]))
                known_admission += amount
            else:
                amount = None
                unknown_fee = True
            unknown_status |= status.status != FieldEvidenceStatus.VERIFIED
            unknown_access |= access.status != FieldEvidenceStatus.VERIFIED
            stops.append(RealPlanStop(idx + 1, place.source_id, place.name,
                place.cultural_category.value, True, _clock(arrival), _clock(current),
                _clock(current + dwell), dwell, amount, fee.status.value,
                access.status.value, "UNKNOWN" if open_min is None or close_min is None else hours.status.value,
                place.latitude, place.longitude, is_assumption, hours.source_url))
            current += dwell
            origin_id, origin_name, origin_lat, origin_lon = place.source_id, place.name, place.latitude, place.longitude
        if not feasible:
            continue
        if round_trip and len(order) > 1:
            final = hub if hub else first
            final_id = final.settlement_id if hub else final.source_id
            if origin_id != final_id:
                route = compute_directed_leg(origin_id, origin_lat, origin_lon, final_id,
                                             final.latitude, final.longitude, transport_mode, routes,
                                             allow_network=allow_network)
                if not route.is_available:
                    route_errors.append(route.failure_reason or "Return leg unreachable")
                    continue
                current += round(route.duration_minutes)
                legs.append(RealPlanLeg(len(legs) + 1, origin_id, origin_name, final_id,
                                        final.name, transport_mode.value, round(route.duration_minutes),
                                        route.distance_km, route.source_name, route.polyline_points))
        elapsed = current - start
        if elapsed > max_minutes:
            continue
        if budget_inr is not None and known_admission > Decimal(str(budget_inr)):
            continue
        unknown_costs = unknown_fee or transport_mode == TransportMode.DRIVING
        total_cost = known_admission if not unknown_costs else None
        level = ("DISCOVERY-ONLY" if unknown_hours or unknown_status else
                 "PROVISIONAL" if unknown_costs or unknown_access or assumption_duration else "VERIFIED")
        reasons = []
        if unknown_hours or unknown_status:
            reasons.append("Illustrative visit order: opening hours or operating status is unverified.")
        if unknown_costs:
            reasons.append("Total cost and budget feasibility are unknown; known admission is a subtotal only.")
        if assumption_duration:
            reasons.append("Visit duration is a traveler input, not a venue fact.")
        if not reasons:
            reasons.append("All required venue fields and directed legs are verified for this visit.")
        plans.append(RealDayPlan("REAL-" + "-".join(p.source_id for p in order), "Fastest available",
            "REAL", hub.name if hub else first.name, day.isoformat(), start_time, elapsed,
            _elapsed(elapsed), len(stops), len(stops), None if unknown_fee else known_admission,
            Decimal("0") if transport_mode == TransportMode.WALKING else None, total_cost, None,
            stops, legs, level, reasons, unknown_costs, transport_mode.value, True, known_admission))
    if not plans:
        reason = route_errors[0] if route_errors else "No order fits the requested time, known hours or known-cost limit."
        return fail(reason)
    fastest = min(plans, key=lambda p: (p.elapsed_minutes, tuple(s.poi_id for s in p.stops)))
    return {"fastest": fastest, "most_cultural": fastest,
            "infeasible_reason": None,
            "comparison_note": "All selected places are cultural; the two objectives produce the same plan."}
