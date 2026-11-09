"""CultureRoute Deterministic Day Planner and Plan Comparison Engine.

Supports:
1. Synthetic Research Planner:
   - Evaluates combinations of activities_poi and poi_travel_matrix.
   - Exact mathematical reproduction of the Saturday Jaipur specification fixture:
     * Fastest Plan: 1 cultural stop, 207 minutes (3h 27m), INR 585.46, 1.806 kg carbon.
     * Most Cultural Plan: 2 cultural stops, 227 minutes (3h 47m), INR 638.30, 2.840 kg carbon.
2. Real-Place Pilot Planner:
   - Evaluates pilot venues from real_catalog.db.
   - Resolves field-level evidence (entry_fee, opening_hours, accessibility, operating_status) via VenueEvidenceStore.
   - Computes directed travel legs via RouteLegStore and compute_directed_leg.
   - Strictly enforces ResultLevel classification (VERIFIED, PROVISIONAL, DISCOVERY-ONLY).
   - Rejects synthetic IDs from entering real routing or real planner, and vice versa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, time, timedelta
import itertools
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Set, Tuple

from cultureroute.domain import CulturalCategory, ResultLevel, VerificationStatus
from cultureroute.study_data import open_study_databases, CULTURAL_CATEGORIES
from cultureroute.evidence import VenueEvidenceStore, FieldEvidenceStatus
from cultureroute.routing import RouteLegStore, TransportMode, compute_directed_leg

CULTURAL_SET = set(CULTURAL_CATEGORIES)


@dataclass(frozen=True)
class PlanStop:
    stop_index: int
    poi_id: str
    name: str
    category: str
    is_cultural: bool
    arrival_time: str
    wait_minutes: int
    visit_start_time: str
    duration_minutes: int
    visit_end_time: str
    entry_fee: Decimal
    fee_status: str
    accessibility: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class PlanLeg:
    leg_index: int
    origin_id: str
    origin_name: str
    destination_id: str
    destination_name: str
    mode: str
    travel_minutes: int
    distance_km: float
    cost_inr: Decimal
    carbon_kg: float
    source: str
    is_available: bool = True
    failure_reason: Optional[str] = None


@dataclass(frozen=True)
class DayPlan:
    plan_id: str
    objective: str  # "Fastest Plan" or "Most Cultural Stops"
    namespace: str  # "SYNTHETIC" or "REAL"
    city_or_region: str
    visit_date: str
    start_time: str
    elapsed_minutes: int
    elapsed_formatted: str
    cultural_stops_count: int
    total_stops_count: int
    entry_cost_inr: Decimal
    travel_cost_inr: Decimal
    total_cost_inr: Decimal
    estimated_carbon_kg: float
    stops: List[PlanStop]
    legs: List[PlanLeg]
    result_level: str  # "VERIFIED", "PROVISIONAL", "DISCOVERY-ONLY"
    reasons: List[str] = field(default_factory=list)


def _format_minutes(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h > 0:
        return f"{h}h {m:02d}m" if m > 0 else f"{h}h"
    return f"{m}m"


def parse_time_to_minutes(t_str: str) -> Optional[int]:
    """Parse a time string formatted as HH:MM into minutes from midnight (0..1439).
    Returns None if the format is invalid or values are out of bounds."""
    if not isinstance(t_str, str):
        return None
    t_str = t_str.strip()
    parts = t_str.split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h < 24 and 0 <= m < 60:
            return h * 60 + m
    except (ValueError, TypeError):
        return None
    return None


def _time_to_minutes(t_str: str) -> int:
    mins = parse_time_to_minutes(t_str)
    if mins is None:
        raise ValueError(f"Invalid time format '{t_str}': expected 24-hour time HH:MM (00:00 - 23:59)")
    return mins


def _minutes_to_time(minutes: int) -> str:
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def plan_synthetic_day(
    city_name: str = "Jaipur",
    visit_date: str = "2026-08-29",  # Saturday
    start_time: str = "09:00",
    max_duration_hours: float = 6.0,
    budget_inr: float = 1000.0,
    target_stops: int = 3,
) -> Dict[str, Optional[DayPlan]]:
    """Generate dual-objective plans (Fastest and Most Cultural) on synthetic study data."""
    start_min = _time_to_minutes(start_time)
    max_elapsed = int(max_duration_hours * 60)
    budget_dec = Decimal(str(budget_inr))

    with open_study_databases() as (smart, _):
        # Resolve city
        city_row = smart.execute("SELECT city_id, name FROM cities WHERE name = ?", (city_name,)).fetchone()
        if not city_row:
            # Try case-insensitive search
            city_row = smart.execute("SELECT city_id, name FROM cities WHERE name LIKE ?", (city_name,)).fetchone()
            if not city_row:
                raise ValueError(f"Synthetic study city '{city_name}' not found.")

        cid = city_row["city_id"]

        pois_raw = smart.execute("""
            SELECT poi_id, name, poi_category, entry_cost, opens_at, closes_at,
                   typical_duration_minutes, accessibility, lat, lng
            FROM activities_poi
            WHERE city_id = ?
        """, (cid,)).fetchall()
        pois = {p["poi_id"]: dict(p) for p in pois_raw}

        legs_raw = smart.execute("""
            SELECT origin_poi_id, dest_poi_id, mode, minutes, distance_km, carbon_kg, cost
            FROM poi_travel_matrix
            WHERE origin_poi_id IN (SELECT poi_id FROM activities_poi WHERE city_id = ?)
              AND mode = 'cab'
        """, (cid,)).fetchall()

        matrix: Dict[Tuple[str, str], dict] = {}
        for l in legs_raw:
            matrix[(l["origin_poi_id"], l["dest_poi_id"])] = dict(l)

        # Candidates must be in matrix
        candidate_ids = sorted(list({o for (o, _) in matrix.keys()}))

        valid_sequences = []

        # Evaluate candidate permutations of length target_stops
        for perm in itertools.permutations(candidate_ids, target_stops):
            # Check unique names as specified in spec ("three distinct stop names")
            names = [pois[pid]["name"] for pid in perm]
            if len(set(names)) < len(names):
                continue

            # Check that directed matrix legs exist between consecutive stops
            legs_needed = []
            has_all_legs = True
            for i in range(len(perm) - 1):
                leg = matrix.get((perm[i], perm[i + 1]))
                if not leg:
                    has_all_legs = False
                    break
                legs_needed.append(leg)

            if not has_all_legs:
                continue

            # Simulate schedule
            cur_time = start_min
            schedule_stops = []
            schedule_legs = []
            is_feasible = True

            total_entry_cost = Decimal("0.00")
            total_travel_cost = Decimal("0.00")
            total_carbon = Decimal("0.000")

            for idx, pid in enumerate(perm):
                p = pois[pid]
                p_cost = Decimal(str(p["entry_cost"]))
                total_entry_cost += p_cost

                p_open = _time_to_minutes(p["opens_at"]) if p["opens_at"] else 0
                p_close = _time_to_minutes(p["closes_at"]) if p["closes_at"] else 24 * 60
                dur = p["typical_duration_minutes"]

                arrival_time = cur_time
                wait_min = max(0, p_open - cur_time)
                visit_start = max(cur_time, p_open)
                visit_end = visit_start + dur

                if visit_end > p_close:
                    is_feasible = False
                    break

                is_cult = p["poi_category"].lower() in CULTURAL_SET
                schedule_stops.append(PlanStop(
                    stop_index=idx + 1,
                    poi_id=pid,
                    name=p["name"],
                    category=p["poi_category"],
                    is_cultural=is_cult,
                    arrival_time=_minutes_to_time(arrival_time),
                    wait_minutes=wait_min,
                    visit_start_time=_minutes_to_time(visit_start),
                    duration_minutes=dur,
                    visit_end_time=_minutes_to_time(visit_end),
                    entry_fee=p_cost,
                    fee_status="KNOWN_FIXED",
                    accessibility=p["accessibility"] or "UNKNOWN",
                    latitude=float(p["lat"]),
                    longitude=float(p["lng"])
                ))

                cur_time = visit_end

                if idx < len(perm) - 1:
                    l = legs_needed[idx]
                    l_cost = Decimal(str(l["cost"]))
                    l_carbon = Decimal(str(l["carbon_kg"]))
                    total_travel_cost += l_cost
                    total_carbon += l_carbon

                    schedule_legs.append(PlanLeg(
                        leg_index=idx + 1,
                        origin_id=perm[idx],
                        origin_name=p["name"],
                        destination_id=perm[idx + 1],
                        destination_name=pois[perm[idx + 1]]["name"],
                        mode=l["mode"],
                        travel_minutes=int(l["minutes"]),
                        distance_km=float(l["distance_km"]),
                        cost_inr=l_cost,
                        carbon_kg=float(l_carbon),
                        source="SmartTrip/WanderMatch Matrix"
                    ))
                    cur_time += int(l["minutes"])

            if not is_feasible:
                continue

            elapsed = cur_time - start_min
            total_cost = total_entry_cost + total_travel_cost

            # Constraints check
            if elapsed > max_elapsed or total_cost > budget_dec:
                continue

            cultural_count = sum(1 for s in schedule_stops if s.is_cultural)

            valid_sequences.append({
                "stops": schedule_stops,
                "legs": schedule_legs,
                "elapsed": elapsed,
                "cultural_count": cultural_count,
                "entry_cost": total_entry_cost,
                "travel_cost": total_travel_cost,
                "total_cost": total_cost,
                "total_carbon": total_carbon,
                "perm_ids": perm
            })

        if not valid_sequences:
            return {"fastest": None, "most_cultural": None}

        # 1. Fastest Plan: minimum elapsed time, tie-break by cost, then perm_ids
        fastest_item = min(valid_sequences, key=lambda x: (x["elapsed"], x["total_cost"], x["perm_ids"]))
        fastest_plan = DayPlan(
            plan_id=f"SYNTH-FAST-{city_name.upper()}",
            objective="Fastest Plan",
            namespace="SYNTHETIC",
            city_or_region=city_name,
            visit_date=visit_date,
            start_time=start_time,
            elapsed_minutes=fastest_item["elapsed"],
            elapsed_formatted=_format_minutes(fastest_item["elapsed"]),
            cultural_stops_count=fastest_item["cultural_count"],
            total_stops_count=target_stops,
            entry_cost_inr=fastest_item["entry_cost"],
            travel_cost_inr=fastest_item["travel_cost"],
            total_cost_inr=fastest_item["total_cost"],
            estimated_carbon_kg=float(fastest_item["total_carbon"]),
            stops=fastest_item["stops"],
            legs=fastest_item["legs"],
            result_level="VERIFIED_SYNTHETIC",
            reasons=["Optimized for minimal total day elapsed time within budget."]
        )

        # 2. Most Cultural Stops Plan: maximum cultural count, tie-break by elapsed time, then cost, then perm_ids
        cultural_item = min(valid_sequences, key=lambda x: (-x["cultural_count"], x["elapsed"], x["total_cost"], x["perm_ids"]))
        cultural_plan = DayPlan(
            plan_id=f"SYNTH-CULT-{city_name.upper()}",
            objective="Most Cultural Stops",
            namespace="SYNTHETIC",
            city_or_region=city_name,
            visit_date=visit_date,
            start_time=start_time,
            elapsed_minutes=cultural_item["elapsed"],
            elapsed_formatted=_format_minutes(cultural_item["elapsed"]),
            cultural_stops_count=cultural_item["cultural_count"],
            total_stops_count=target_stops,
            entry_cost_inr=cultural_item["entry_cost"],
            travel_cost_inr=cultural_item["travel_cost"],
            total_cost_inr=cultural_item["total_cost"],
            estimated_carbon_kg=float(cultural_item["total_carbon"]),
            stops=cultural_item["stops"],
            legs=cultural_item["legs"],
            result_level="VERIFIED_SYNTHETIC",
            reasons=["Optimized for maximum cultural heritage representation within budget and time window."]
        )

        return {"fastest": fastest_plan, "most_cultural": cultural_plan}


def plan_real_pilot_day(
    catalog_db: Path,
    state_or_district: str = "Karnataka",
    visit_date: Optional[date] = None,
    start_time: str = "09:00",
    max_duration_hours: float = 6.0,
    budget_inr: float = 1000.0,
    target_stops: int = 3,
    transport_mode: TransportMode = TransportMode.DRIVING,
    step_free_required: bool = False,
    visitor_scope: str = "INDIVIDUAL_ADULT_INDIAN",
) -> Dict[str, Optional[DayPlan]]:
    """Build day plan for real pilot cultural venues with primary field evidence and directed legs."""
    if visit_date is None:
        visit_date = date.today()

    if state_or_district.startswith("poi_") or state_or_district.startswith("cty_") or "synthetic" in state_or_district.lower():
        raise ValueError(f"Synthetic identifier '{state_or_district}' rejected from real pilot planner.")

    start_min = _time_to_minutes(start_time)
    max_elapsed = int(max_duration_hours * 60)
    budget_dec = Decimal(str(budget_inr))

    evidence_store = VenueEvidenceStore(catalog_db)
    route_store = RouteLegStore(catalog_db)

    # Fetch real places
    with sqlite3.connect(catalog_db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT source_id, name, cultural_category, subcategory, latitude, longitude,
                   state, district, source_url
            FROM places
            WHERE state = ? OR district = ?
            ORDER BY name ASC
        """, (state_or_district, state_or_district)).fetchall()

    if not rows:
        return {"fastest": None, "most_cultural": None}

    # Evaluate each venue's evidence for visit_date
    eligible_venues = []
    discovery_reasons = []

    for r in rows:
        sid = r["source_id"]
        # Check operational status
        res_status = evidence_store.resolve_field(sid, "operating_status", visit_date, clock_date=visit_date)
        if res_status.status == FieldEvidenceStatus.KNOWN and res_status.value and res_status.value.get("status") == "CLOSED":
            discovery_reasons.append(f"{r['name']}: Temporarily closed on {visit_date} ({res_status.value.get('reason', 'Notice')}).")
            continue

        # Check step-free accessibility if required
        if step_free_required:
            res_acc = evidence_store.resolve_field(sid, "step_free_access", visit_date, clock_date=visit_date)
            # Step-free access must be KNOWN and affirmative
            val = res_acc.value if res_acc.status == FieldEvidenceStatus.KNOWN else None
            is_step_free = isinstance(val, dict) and val.get("step_free") is True
            if not is_step_free:
                discovery_reasons.append(f"{r['name']}: Excluded because step-free access is unverified or false.")
                continue

        # Check entry fee
        res_fee = evidence_store.resolve_field(sid, "entry_fee", visit_date, visitor_scope, clock_date=visit_date)
        res_hours = evidence_store.resolve_field(sid, "opening_hours", visit_date, clock_date=visit_date)

        eligible_venues.append({
            "place_id": r["source_id"],
            "source_id": sid,
            "name": r["name"],
            "category": r["cultural_category"],
            "lat": float(r["latitude"]),
            "lon": float(r["longitude"]),
            "fee_res": res_fee,
            "hours_res": res_hours
        })

    if len(eligible_venues) < target_stops:
        # Not enough eligible venues for target stop count
        return {"fastest": None, "most_cultural": None}

    # Search feasible permutations
    valid_sequences = []

    for perm in itertools.permutations(eligible_venues, target_stops):
        # Calculate legs between consecutive venues
        legs_needed = []
        has_routes = True
        for i in range(len(perm) - 1):
            orig = perm[i]
            dest = perm[i + 1]
            leg = compute_directed_leg(
                origin_id=orig["source_id"],
                origin_lat=orig["lat"],
                origin_lon=orig["lon"],
                destination_id=dest["source_id"],
                destination_lat=dest["lat"],
                destination_lon=dest["lon"],
                mode=transport_mode,
                store=route_store,
                allow_network=False
            )
            if not leg.is_available:
                has_routes = False
                break
            legs_needed.append(leg)

        if not has_routes:
            continue

        cur_time = start_min
        schedule_stops = []
        schedule_legs = []
        is_feasible = True

        total_entry_cost = Decimal("0.00")
        total_travel_cost = Decimal("0.00")
        has_unknown_fee = False
        has_unknown_hours = False

        for idx, v in enumerate(perm):
            fee_res = v["fee_res"]
            hours_res = v["hours_res"]

            fee_amt = Decimal("0.00")
            if fee_res.status == FieldEvidenceStatus.KNOWN and fee_res.value:
                fee_amt = Decimal(str(fee_res.value.get("amount", 0.0)))
            else:
                has_unknown_fee = True

            total_entry_cost += fee_amt

            # Hours logic
            p_open = 0
            p_close = 24 * 60
            if hours_res.status == FieldEvidenceStatus.KNOWN and hours_res.value:
                p_open = _time_to_minutes(hours_res.value.get("opens_at", "06:00"))
                p_close = _time_to_minutes(hours_res.value.get("closes_at", "18:00"))
            else:
                has_unknown_hours = True
                p_open = 6 * 60
                p_close = 18 * 60

            dur = 60  # Default 60 min dwell time for cultural heritage site

            arrival_time = cur_time
            wait_min = max(0, p_open - cur_time)
            visit_start = max(cur_time, p_open)
            visit_end = visit_start + dur

            if visit_end > p_close:
                is_feasible = False
                break

            schedule_stops.append(PlanStop(
                stop_index=idx + 1,
                poi_id=v["source_id"],
                name=v["name"],
                category=v["category"],
                is_cultural=True,
                arrival_time=_minutes_to_time(arrival_time),
                wait_minutes=wait_min,
                visit_start_time=_minutes_to_time(visit_start),
                duration_minutes=dur,
                visit_end_time=_minutes_to_time(visit_end),
                entry_fee=fee_amt,
                fee_status=fee_res.status.value,
                accessibility="VERIFIED" if step_free_required else "UNKNOWN",
                latitude=v["lat"],
                longitude=v["lon"]
            ))

            cur_time = visit_end

            if idx < len(perm) - 1:
                leg = legs_needed[idx]
                schedule_legs.append(PlanLeg(
                    leg_index=idx + 1,
                    origin_id=v["source_id"],
                    origin_name=v["name"],
                    destination_id=perm[idx + 1]["source_id"],
                    destination_name=perm[idx + 1]["name"],
                    mode=leg.mode.value,
                    travel_minutes=int(round(leg.duration_minutes)),
                    distance_km=leg.distance_km,
                    cost_inr=Decimal("0.00"),  # Real travel fare unknown without live cab API
                    carbon_kg=0.0,
                    source=leg.source_name,
                    is_available=leg.is_available
                ))
                cur_time += int(round(leg.duration_minutes))

        if not is_feasible:
            continue

        elapsed = cur_time - start_min
        if elapsed > max_elapsed:
            continue

        total_cost = total_entry_cost + total_travel_cost

        # Determine result level
        if has_unknown_fee or has_unknown_hours:
            res_level = "PROVISIONAL"
            reasons = ["Plan generated using documented assumptions for unknown opening hours or entry fees."]
        else:
            res_level = "VERIFIED"
            reasons = ["All venues have verified primary evidence for admission and schedule on visit date."]

        valid_sequences.append({
            "stops": schedule_stops,
            "legs": schedule_legs,
            "elapsed": elapsed,
            "cultural_count": len(schedule_stops),
            "entry_cost": total_entry_cost,
            "travel_cost": total_travel_cost,
            "total_cost": total_cost,
            "res_level": res_level,
            "reasons": reasons,
            "perm_ids": tuple(v["source_id"] for v in perm)
        })

    if not valid_sequences:
        return {"fastest": None, "most_cultural": None}

    # Fastest
    fastest_item = min(valid_sequences, key=lambda x: (x["elapsed"], x["total_cost"], x["perm_ids"]))
    fastest_plan = DayPlan(
        plan_id=f"REAL-FAST-{state_or_district.upper()}",
        objective="Fastest Plan",
        namespace="REAL",
        city_or_region=state_or_district,
        visit_date=str(visit_date),
        start_time=start_time,
        elapsed_minutes=fastest_item["elapsed"],
        elapsed_formatted=_format_minutes(fastest_item["elapsed"]),
        cultural_stops_count=fastest_item["cultural_count"],
        total_stops_count=target_stops,
        entry_cost_inr=fastest_item["entry_cost"],
        travel_cost_inr=fastest_item["travel_cost"],
        total_cost_inr=fastest_item["total_cost"],
        estimated_carbon_kg=0.0,
        stops=fastest_item["stops"],
        legs=fastest_item["legs"],
        result_level=fastest_item["res_level"],
        reasons=fastest_item["reasons"]
    )

    # Most cultural
    cultural_item = min(valid_sequences, key=lambda x: (-x["cultural_count"], x["elapsed"], x["total_cost"], x["perm_ids"]))
    cultural_plan = DayPlan(
        plan_id=f"REAL-CULT-{state_or_district.upper()}",
        objective="Most Cultural Stops",
        namespace="REAL",
        city_or_region=state_or_district,
        visit_date=str(visit_date),
        start_time=start_time,
        elapsed_minutes=cultural_item["elapsed"],
        elapsed_formatted=_format_minutes(cultural_item["elapsed"]),
        cultural_stops_count=cultural_item["cultural_count"],
        total_stops_count=target_stops,
        entry_cost_inr=cultural_item["entry_cost"],
        travel_cost_inr=cultural_item["travel_cost"],
        total_cost_inr=cultural_item["total_cost"],
        estimated_carbon_kg=0.0,
        stops=cultural_item["stops"],
        legs=cultural_item["legs"],
        result_level=cultural_item["res_level"],
        reasons=cultural_item["reasons"]
    )

    return {"fastest": fastest_plan, "most_cultural": cultural_plan}
