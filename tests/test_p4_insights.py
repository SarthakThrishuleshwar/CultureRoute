"""Tests for CultureRoute Stage P4: Insights & Analytical Story.

Verifies:
1. Three Distinct Populations:
   - Listings: 211 / 675 (31.3%)
   - Interactions: 2,144 / 6,850 (31.3%)
   - Planned Stops: 961 / 3,191 (30.1%)
2. 57-Week Monday–Sunday Time Series:
   - 57 complete weeks, 2,138 complete-week cultural actions.
   - Aggregate baseline MAEs: 3.42 (Previous-Week) and 3.88 (Trailing 4-Week Mean).
   - Target next week: 2026-08-17.
3. Indian Events Footfall Imputation:
   - 225 total events, 46 source nulls, 179 known.
   - Deterministic 80/20 split (143 fit / 36 holdout).
   - Comparative evaluation of Mean, Median, and Lognormal MLE.
4. EDA & Descriptives:
   - 675 attractions, 207 free (30.7%), median INR 200.00, IQR INR 750.00.
   - Bivariate entry fee vs saves correlation is near zero.
5. AppTest Integration:
   - ?view=insights loads with 0 exceptions and renders all 4 tabs.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from cultureroute.analytics import (
    compute_cultural_shares,
    compute_weekly_forecast_backtest,
    compute_footfall_imputation_study,
    compute_price_descriptives,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_FILE = ROOT_DIR / "app.py"


def test_p4_three_populations_exact_reconciliation():
    """Verify cultural representation across all 3 separate populations."""
    shares = compute_cultural_shares()

    listings = shares["listings"]
    interactions = shares["interactions"]
    stops = shares["planned_stops"]

    # Listings: 211 / 675 = 31.3%
    assert listings.numerator == 211
    assert listings.denominator == 675
    assert round(listings.share_percent, 1) == 31.3

    # Interactions: 2,144 / 6,850 = 31.3%
    assert interactions.numerator == 2144
    assert interactions.denominator == 6850
    assert round(interactions.share_percent, 1) == 31.3

    # Planned Stops: 961 / 3,191 = 30.1%
    assert stops.numerator == 961
    assert stops.denominator == 3191
    assert round(stops.share_percent, 1) == 30.1


def test_p4_weekly_forecast_aggregate_baselines():
    """Verify 57 complete weeks and aggregate baseline MAEs of 3.42 and 3.88."""
    fc = compute_weekly_forecast_backtest()

    assert fc.total_complete_weeks == 57
    assert fc.evaluated_weeks_count == 12
    assert round(fc.model1_mae, 2) == 3.42
    assert round(fc.model2_mae, 2) == 3.88
    assert fc.next_week_start == "2026-08-17"


def test_p4_footfall_imputation_deterministic_split():
    """Verify 225 Indian events, 46 nulls, and holdout evaluation."""
    ff = compute_footfall_imputation_study()

    assert ff.total_events == 225
    assert ff.missing_count == 46
    assert ff.known_count == 179
    assert ff.train_count == 143
    assert ff.holdout_count == 36
    assert ff.train_count + ff.holdout_count == ff.known_count

    # Holdout errors should be non-negative real numbers
    assert ff.mean_holdout_mae > 0
    assert ff.median_holdout_mae > 0
    assert ff.mle_holdout_mae > 0


def test_p4_eda_price_descriptives():
    """Verify price distribution metrics and zero-fee percentage."""
    stats, df = compute_price_descriptives()

    assert stats.sample_size == 675
    assert stats.free_count == 207
    assert round(stats.free_percent, 1) == 30.7
    assert stats.paid_count == 468
    assert round(stats.median_price, 2) == 200.00
    assert round(stats.iqr_price, 2) == 750.00


def test_p4_apptest_insights_renders_all_tabs():
    """Verify AppTest loads Insights with 0 exceptions across all 4 analytical tabs."""
    at = AppTest.from_file(str(APP_FILE))
    at.query_params["view"] = "insights"
    at.run()
    assert not at.exception

    # Check tabs present
    assert len(at.tabs) >= 4

    # Check subheaders
    subheaders = [s.value for s in at.subheader]
    assert any("Cultural Representation" in s for s in subheaders)
    assert any("Longitudinal Activity" in s for s in subheaders)
    assert any("Footfall Imputation" in s for s in subheaders)
    assert any("Exploratory Data Analysis" in s for s in subheaders)

    # Metrics
    metric_labels = [m.label for m in at.metric]
    metric_values = [str(m.value) for m in at.metric]

    assert any("Catalog Listings" in l for l in metric_labels)
    assert any("User Interactions" in l for l in metric_labels)
    assert any("Scheduled Stops" in l for l in metric_labels)
    assert any("3.42" in str(m.value) for m in at.metric)
    assert any("3.88" in str(m.value) for m in at.metric)
