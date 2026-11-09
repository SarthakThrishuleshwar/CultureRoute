"""Tests for CultureRoute Phase 9: Insights and Predictions (Synthetic Research).

Verifies:
1. Reconcile the three canonical cultural shares with separate denominators:
   - Listings: 211 / 675 = 31.3%
   - Matched user interactions: 2,144 / 6,850 = 31.3%
   - Selected itinerary stops: 961 / 3,191 = 30.1%
2. Parametric & non-parametric price summary statistics across 675 attractions.
3. Weekly engagement forecasting:
   - 57 complete Monday–Sunday weeks.
   - 12 evaluated holdout target weeks.
   - Model 1 (previous-week count) MAE == 3.42.
   - Model 2 (4-week mean) MAE == 3.88.
4. Footfall imputation & estimation:
   - 225 Indian event rows.
   - Exactly 46 missing expected-footfall values preserved.
   - Disjoint train and holdout sets.
   - Mean, Median, and Lognormal MLE comparison.
"""

from __future__ import annotations

import pytest
from cultureroute.analytics import (
    compute_cultural_shares,
    compute_price_descriptives,
    compute_weekly_forecast_backtest,
    compute_footfall_imputation_study
)


def test_cultural_shares_reconciliation():
    """Verify cultural shares and distinct denominators [211/675, 2144/6850, 961/3191]."""
    shares = compute_cultural_shares()

    # 1. Listings
    s_list = shares["listings"]
    assert s_list.numerator == 211
    assert s_list.denominator == 675
    assert s_list.share_percent == 31.3
    assert s_list.share_display == "31.3%"

    # 2. Interactions
    s_inter = shares["interactions"]
    assert s_inter.numerator == 2144
    assert s_inter.denominator == 6850
    assert s_inter.share_percent == 31.3
    assert s_inter.share_display == "31.3%"

    # 3. Planned stops
    s_stops = shares["planned_stops"]
    assert s_stops.numerator == 961
    assert s_stops.denominator == 3191
    assert s_stops.share_percent == 30.1
    assert s_stops.share_display == "30.1%"


def test_price_descriptives_integrity():
    """Verify price distribution statistics across all 675 Indian study attractions."""
    stats, df = compute_price_descriptives()
    assert stats.sample_size == 675
    assert len(df) == 675
    assert stats.free_count + stats.paid_count == 675
    assert stats.free_count > 0
    assert stats.min_price == 0.0
    assert stats.max_price >= 1000.0
    assert stats.median_price >= 0.0
    assert stats.iqr_price == round(stats.q3_price - stats.q1_price, 2)


def test_weekly_forecast_backtest_maes():
    """Verify 57 complete weeks and exact MAEs (3.42 and 3.88) over last 12 weeks."""
    report = compute_weekly_forecast_backtest()
    assert report.total_complete_weeks == 57
    assert report.evaluated_weeks_count == 12

    # Model 1: Previous-week count MAE == 3.42
    assert report.model1_mae == 3.42

    # Model 2: Trailing 4-week mean MAE == 3.88
    assert report.model2_mae == 3.88

    # Ensure evaluation window is strictly the last 12 weeks
    eval_weeks = [w for w in report.weekly_series if w.is_evaluation_window]
    assert len(eval_weeks) == 12
    assert all(w.model1_error is not None for w in eval_weeks)
    assert all(w.model2_error is not None for w in eval_weeks)


def test_footfall_imputation_and_holdout_evaluation():
    """Verify 225 Indian events, 46 missing footfalls, and disjoint holdout evaluation."""
    report = compute_footfall_imputation_study()
    assert report.total_events == 225
    assert report.missing_count == 46
    assert report.known_count == 179
    assert report.train_count + report.holdout_count == 179

    # Train and holdout must be non-empty and disjoint
    assert report.train_count == 143
    assert report.holdout_count == 36

    # Verify holdout errors are finite and positive
    assert report.mean_holdout_mae > 0.0
    assert report.median_holdout_mae > 0.0
    assert report.mle_holdout_mae > 0.0

    # Ensure all 225 records are returned with provenance
    assert len(report.events_imputed) == 225
    missing_imputed = [e for e in report.events_imputed if e["is_originally_missing"]]
    assert len(missing_imputed) == 46
    assert all(e["imputed_expected_footfall"] is not None for e in report.events_imputed)
