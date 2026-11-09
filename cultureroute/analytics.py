"""CultureRoute Synthetic Research Analytics & Predictions Engine (Phase 9).

Provides:
1. Cultural Share Analysis:
   - Listings share: 211 / 675 = 31.3%
   - Matched Interactions share: 2,144 / 6,850 = 31.3%
   - Selected Itinerary Stops share: 961 / 3,191 = 30.1%
2. Descriptive Statistics:
   - Price distribution (mean, median, IQR, std, quartiles, free vs paid).
   - Category representation across 45 Indian study cities.
3. Time-Series Engagement Forecasting:
   - 57 complete Monday–Sunday weeks.
   - Model 1: Previous-week count (Last-12 MAE: 3.42).
   - Model 2: Trailing 4-week mean (Last-12 MAE: 3.88).
4. Missing Footfall Imputation & Maximum-Likelihood Evaluation:
   - 225 Indian events, 46 missing expected footfall values.
   - Disjoint holdout evaluation on 179 known rows comparing Mean, Median, and Lognormal MLE.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
import math
from pathlib import Path
import statistics
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from cultureroute.study_data import open_study_databases, _scoped_selected_sql, CULTURAL_CATEGORIES

CULTURAL_SET = set(CULTURAL_CATEGORIES)


@dataclass(frozen=True)
class CulturalShareMetric:
    population: str
    numerator: int
    denominator: int
    share_ratio: float
    share_percent: float
    share_display: str
    definition: str


@dataclass(frozen=True)
class PriceDescriptives:
    sample_size: int
    free_count: int
    free_percent: float
    paid_count: int
    paid_percent: float
    mean_price: float
    median_price: float
    std_price: float
    q1_price: float
    q3_price: float
    iqr_price: float
    min_price: float
    max_price: float


@dataclass(frozen=True)
class ForecastWeek:
    week_start: str
    actual: int
    model1_pred: Optional[float]
    model2_pred: Optional[float]
    model1_error: Optional[float]
    model2_error: Optional[float]
    is_evaluation_window: bool


@dataclass(frozen=True)
class ForecastReport:
    total_complete_weeks: int
    evaluated_weeks_count: int
    model1_name: str
    model1_mae: float
    model2_name: str
    model2_mae: float
    weekly_series: List[ForecastWeek]
    next_week_start: Optional[str] = None
    next_week_model1: Optional[float] = None
    next_week_model2: Optional[float] = None


@dataclass(frozen=True)
class FootfallImputationReport:
    total_events: int
    missing_count: int
    known_count: int
    train_count: int
    holdout_count: int
    mean_train_val: float
    median_train_val: float
    mle_mu: float
    mle_sigma: float
    mle_median_val: float
    mean_holdout_mae: float
    median_holdout_mae: float
    mle_holdout_mae: float
    recommended_imputer: str
    events_imputed: List[Dict[str, Any]]


@lru_cache(maxsize=16)
def compute_cultural_shares() -> Dict[str, CulturalShareMetric]:
    """Compute the three canonical cultural shares with separate denominators."""
    with open_study_databases() as (smart, _):
        # 1. Listings
        poi_total = int(smart.execute(
            "SELECT count(*) FROM activities_poi a JOIN cities c USING(city_id) WHERE c.country_code='IN'"
        ).fetchone()[0])
        cultural_poi = int(smart.execute(
            "SELECT count(*) FROM activities_poi a JOIN cities c USING(city_id) "
            "WHERE c.country_code='IN' AND a.poi_category IN ('heritage','museum','religious','food')"
        ).fetchone()[0])

        # 2. Matched Interactions
        interaction_where = (
            "FROM wm.user_interactions u "
            "JOIN activities_poi a ON u.entity_type='poi' AND u.entity_id=a.poi_id "
            "JOIN cities c ON c.city_id=a.city_id WHERE c.country_code='IN'"
        )
        interactions_total = int(smart.execute(f"SELECT count(*) {interaction_where}").fetchone()[0])
        cultural_interactions = int(smart.execute(
            f"SELECT count(*) {interaction_where} AND a.poi_category IN ('heritage','museum','religious','food')"
        ).fetchone()[0])

        # 3. Selected Itinerary Stops
        stops_total = int(smart.execute(_scoped_selected_sql()).fetchone()[0])
        cultural_stops = int(smart.execute(
            _scoped_selected_sql() + " AND a.poi_category IN ('heritage','museum','religious','food')"
        ).fetchone()[0])

    r_listings = cultural_poi / poi_total if poi_total else 0.0
    r_interactions = cultural_interactions / interactions_total if interactions_total else 0.0
    r_stops = cultural_stops / stops_total if stops_total else 0.0

    return {
        "listings": CulturalShareMetric(
            population="Attraction Listings",
            numerator=cultural_poi,
            denominator=poi_total,
            share_ratio=r_listings,
            share_percent=round(r_listings * 100, 1),
            share_display=f"{round(r_listings * 100, 1)}%",
            definition="Proportion of Indian catalog attractions classified as heritage, museum, religious, or food."
        ),
        "interactions": CulturalShareMetric(
            population="Matched User Interactions",
            numerator=cultural_interactions,
            denominator=interactions_total,
            share_ratio=r_interactions,
            share_percent=round(r_interactions * 100, 1),
            share_display=f"{round(r_interactions * 100, 1)}%",
            definition="Proportion of verified user views/saves/bookings directed to cultural attractions."
        ),
        "planned_stops": CulturalShareMetric(
            population="Selected Itinerary Stops",
            numerator=cultural_stops,
            denominator=stops_total,
            share_ratio=r_stops,
            share_percent=round(r_stops * 100, 1),
            share_display=f"{round(r_stops * 100, 1)}%",
            definition="Proportion of confirmed stops on non-cancelled itineraries visiting cultural attractions."
        )
    }


@lru_cache(maxsize=16)
def compute_price_descriptives() -> Tuple[PriceDescriptives, pd.DataFrame]:
    """Compute parametric and non-parametric summary statistics on attraction entry prices."""
    with open_study_databases() as (smart, _):
        rows = smart.execute("""
            SELECT a.poi_id, a.name, a.poi_category, c.name as city_name, CAST(a.entry_cost AS REAL) as price
            FROM activities_poi a
            JOIN cities c USING(city_id)
            WHERE c.country_code = 'IN'
            ORDER BY price ASC
        """).fetchall()

    df = pd.DataFrame([dict(r) for r in rows])
    prices = df["price"].dropna().tolist()
    n = len(prices)

    free_count = sum(1 for p in prices if p == 0.0)
    paid_count = n - free_count
    mean_val = statistics.mean(prices)
    median_val = statistics.median(prices)
    std_val = statistics.stdev(prices) if n > 1 else 0.0

    # Quantiles
    prices_sorted = sorted(prices)
    q1 = prices_sorted[int(n * 0.25)]
    q3 = prices_sorted[int(n * 0.75)]
    iqr = q3 - q1

    stats = PriceDescriptives(
        sample_size=n,
        free_count=free_count,
        free_percent=round((free_count / n) * 100, 1),
        paid_count=paid_count,
        paid_percent=round((paid_count / n) * 100, 1),
        mean_price=round(mean_val, 2),
        median_price=round(median_val, 2),
        std_price=round(std_val, 2),
        q1_price=round(q1, 2),
        q3_price=round(q3, 2),
        iqr_price=round(iqr, 2),
        min_price=round(min(prices), 2),
        max_price=round(max(prices), 2)
    )

    return stats, df


@lru_cache(maxsize=16)
def compute_weekly_forecast_backtest() -> ForecastReport:
    """Evaluate weekly cultural engagement forecasting models over the last 12 complete weeks."""
    with open_study_databases() as (smart, _):
        cultural_pred = "('heritage','museum','religious','food')"
        interaction_where = (
            "FROM wm.user_interactions u "
            "JOIN activities_poi a ON u.entity_type='poi' AND u.entity_id=a.poi_id "
            "JOIN cities c ON c.city_id=a.city_id WHERE c.country_code='IN'"
        )
        timestamps = smart.execute(
            f"SELECT u.occurred_at {interaction_where} AND a.poi_category IN {cultural_pred}"
        ).fetchall()

    weekly: Counter = Counter()
    for (ts,) in timestamps:
        d = datetime.fromisoformat(ts).date()
        week_monday = d - timedelta(days=d.weekday())
        weekly[week_monday] += 1

    weeks_sorted = sorted(weekly.keys())
    complete_weeks = weeks_sorted[:-1]  # Exclude partial trailing week
    values = [weekly[w] for w in complete_weeks]
    n_weeks = len(complete_weeks)

    m1_errors = []
    m2_errors = []
    series_report: List[ForecastWeek] = []

    for i in range(n_weeks):
        w_date = complete_weeks[i]
        act = values[i]
        m1_pred = float(values[i - 1]) if i >= 1 else None
        m2_pred = float(sum(values[i - 4:i]) / 4.0) if i >= 4 else None

        is_eval = i >= (n_weeks - 12)

        m1_err = abs(act - m1_pred) if (is_eval and m1_pred is not None) else None
        m2_err = abs(act - m2_pred) if (is_eval and m2_pred is not None) else None

        if is_eval and m1_err is not None:
            m1_errors.append(m1_err)
        if is_eval and m2_err is not None:
            m2_errors.append(m2_err)

        series_report.append(ForecastWeek(
            week_start=str(w_date),
            actual=act,
            model1_pred=round(m1_pred, 1) if m1_pred is not None else None,
            model2_pred=round(m2_pred, 2) if m2_pred is not None else None,
            model1_error=round(m1_err, 2) if m1_err is not None else None,
            model2_error=round(m2_err, 2) if m2_err is not None else None,
            is_evaluation_window=is_eval
        ))

    mae1 = round(sum(m1_errors) / len(m1_errors), 2) if m1_errors else 0.0
    mae2 = round(sum(m2_errors) / len(m2_errors), 2) if m2_errors else 0.0

    next_w_start = str(complete_weeks[-1] + timedelta(days=7)) if n_weeks > 0 else None
    next_m1 = float(values[-1]) if n_weeks > 0 else None
    next_m2 = round(float(sum(values[-4:]) / 4.0), 2) if n_weeks >= 4 else None

    return ForecastReport(
        total_complete_weeks=n_weeks,
        evaluated_weeks_count=len(m1_errors),
        model1_name="Previous-Week Count",
        model1_mae=mae1,
        model2_name="Trailing 4-Week Mean",
        model2_mae=mae2,
        weekly_series=series_report,
        next_week_start=next_w_start,
        next_week_model1=next_m1,
        next_week_model2=next_m2,
    )


@lru_cache(maxsize=16)
def compute_footfall_imputation_study() -> FootfallImputationReport:
    """Evaluate missing expected-footfall imputation with a deterministic holdout split."""
    with open_study_databases() as (smart, _):
        rows = smart.execute("""
            SELECT e.event_id, e.name, c.name as city_name, e.expected_footfall
            FROM events_festivals e
            JOIN cities c USING(city_id)
            WHERE c.country_code = 'IN'
            ORDER BY e.event_id ASC
        """).fetchall()

    total_events = len(rows)
    known_events = []
    missing_events = []

    for r in rows:
        d = dict(r)
        if d["expected_footfall"] is not None:
            d["expected_footfall"] = float(d["expected_footfall"])
            known_events.append(d)
        else:
            missing_events.append(d)

    n_known = len(known_events)
    # Deterministic split: first 80% train, last 20% holdout (order by event_id)
    n_train = int(n_known * 0.8)
    train_set = known_events[:n_train]
    holdout_set = known_events[n_train:]

    train_vals = [e["expected_footfall"] for e in train_set]
    holdout_vals = [e["expected_footfall"] for e in holdout_set]

    # Model A: Mean
    mean_fit = statistics.mean(train_vals)
    mae_mean = sum(abs(v - mean_fit) for v in holdout_vals) / len(holdout_vals)

    # Model B: Median
    median_fit = statistics.median(train_vals)
    mae_median = sum(abs(v - median_fit) for v in holdout_vals) / len(holdout_vals)

    # Model C: Parametric Lognormal Maximum Likelihood Estimation
    # log(Y) ~ Normal(mu, sigma^2)
    log_vals = [math.log(max(1.0, v)) for v in train_vals]
    mle_mu = statistics.mean(log_vals)
    mle_var = sum((x - mle_mu) ** 2 for x in log_vals) / len(log_vals)
    mle_sigma = math.sqrt(mle_var)
    # Median of lognormal distribution is exp(mu)
    mle_median = math.exp(mle_mu)
    mae_mle = sum(abs(v - mle_median) for v in holdout_vals) / len(holdout_vals)

    # Choose best imputer for reporting
    best_imputer = "Median"
    best_val = median_fit
    if mae_mle < mae_median and mae_mle < mae_mean:
        best_imputer = "Lognormal MLE (Median exp(mu))"
        best_val = mle_median

    imputed_records = []
    for r in rows:
        orig = r["expected_footfall"]
        is_missing = orig is None
        imputed_val = round(best_val, 0) if is_missing else float(orig)
        imputed_records.append({
            "event_id": r["event_id"],
            "name": r["name"],
            "city": r["city_name"],
            "original_expected_footfall": orig,
            "is_originally_missing": is_missing,
            "imputed_expected_footfall": imputed_val,
            "imputation_method": best_imputer if is_missing else "OBSERVED_ORIGINAL"
        })

    return FootfallImputationReport(
        total_events=total_events,
        missing_count=len(missing_events),
        known_count=n_known,
        train_count=n_train,
        holdout_count=len(holdout_set),
        mean_train_val=round(mean_fit, 1),
        median_train_val=round(median_fit, 1),
        mle_mu=round(mle_mu, 3),
        mle_sigma=round(mle_sigma, 3),
        mle_median_val=round(mle_median, 1),
        mean_holdout_mae=round(mae_mean, 1),
        median_holdout_mae=round(mae_median, 1),
        mle_holdout_mae=round(mae_mle, 1),
        recommended_imputer=best_imputer,
        events_imputed=imputed_records
    )
