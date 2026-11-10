"""CultureRoute Deterministic Day Planner and Plan Comparison Engine.

Supports:
1. Synthetic Research Planner:
   - Evaluates combinations of activities_poi and poi_travel_matrix.
   - Exact mathematical reproduction of the Saturday Jaipur specification fixture:
     * Fastest Plan: 1 cultural stop, 207 minutes (3h 27m), INR 585.46, 1.806 kg carbon.
     * Most Cultural Plan: 2 cultural stops, 227 minutes (3h 47m), INR 638.30, 2.840 kg carbon.
2. Real-place planning is implemented in real_planner.py with separate stores and
   re-exported here for the Streamlit entry point.
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
from cultureroute.real_planner import plan_real_place_day

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
    hours_status: str = "EXACT_VERIFIED"


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
    matrix_id: str = ""
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
    has_uncertain_hours: bool = False
    transport_mode: str = "cab"


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
    transport_mode: str = "cab",
    step_free_only: bool = False,
    preferred_categories: Optional[List[str]] = None,
) -> Dict[str, Optional[DayPlan]]:
    """Generate dual-objective plans (Fastest and Most Cultural) on synthetic study data."""
    start_min = _time_to_minutes(start_time)
    max_elapsed = int(max_duration_hours * 60)
    budget_dec = Decimal(str(budget_inr))
    if transport_mode not in ("cab", "walk"):
        raise ValueError("Study transport mode must be cab or walk")
    if max_duration_hours <= 0:
        raise ValueError("Available duration must be positive")
    if budget_inr <= 0:
        raise ValueError("Budget must be positive")
    if target_stops < 2 or target_stops > 5:
        raise ValueError("Target stops must be between 2 and 5")
    try:
        weekday = date.fromisoformat(visit_date).weekday()
    except (ValueError, TypeError):
        raise ValueError("Invalid visit date") from None

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
            SELECT poi_id, name, poi_category, entry_cost, currency, status,
                   opens_at, closes_at, closed_days,
                   typical_duration_minutes, accessibility, lat, lng
            FROM activities_poi
            WHERE city_id = ?
        """, (cid,)).fetchall()
        pois = {p["poi_id"]: dict(p) for p in pois_raw}

        legs_raw = smart.execute("""
            SELECT matrix_id, origin_poi_id, dest_poi_id, mode, minutes, distance_km, carbon_kg, cost
            FROM poi_travel_matrix
            WHERE origin_poi_id IN (SELECT poi_id FROM activities_poi WHERE city_id = ?)
              AND mode = ?
        """, (cid, transport_mode)).fetchall()

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
                if p["status"] != "active" or p["currency"] != "INR":
                    is_feasible = False
                    break
                if step_free_only and p["accessibility"] != "step_free":
                    is_feasible = False
                    break
                if p["closed_days"] and str(weekday) in str(p["closed_days"]).split(","):
                    is_feasible = False
                    break
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
                    longitude=float(p["lng"]),
                    hours_status=("EXACT_VERIFIED" if p["opens_at"] and p["closes_at"]
                                  else "CONDITIONAL_UNKNOWN_HOURS")
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
                        source="SmartTrip/WanderMatch Matrix",
                        matrix_id=l["matrix_id"]
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
            reasons=["Optimized for minimal total day elapsed time within budget."],
            has_uncertain_hours=any(s.hours_status != "EXACT_VERIFIED" for s in fastest_item["stops"]),
            transport_mode=transport_mode
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
            reasons=["Optimized for maximum cultural heritage representation within budget and time window."],
            has_uncertain_hours=any(s.hours_status != "EXACT_VERIFIED" for s in cultural_item["stops"]),
            transport_mode=transport_mode
        )

        return {"fastest": fastest_plan, "most_cultural": cultural_plan}
