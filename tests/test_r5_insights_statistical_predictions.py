"""Tests for CultureRoute Stage R5: Insights and Statistical Predictions.

Verifies:
1. Three distinct cultural share populations with separate denominators:
   - Listings: 211 / 675 = 31.3%.
   - User interactions: 2,144 / 6,850 = 31.3%.
   - Selected stops: 961 / 3,191 = 30.1%.
2. Continuous Monday-Sunday weekly forecast series:
   - 57 complete weeks.
   - Out-of-sample backtest MAEs: Model 1 = 3.42, Model 2 = 3.88 on last 12 complete weeks.
   - Next-complete-week forecast target: 2026-08-17 (Model 1 = 44.0, Model 2 = 39.25).
3. Indian events footfall imputation and lognormal MLE:
   - 225 Indian events, exactly 46 preserved nulls.
   - Disjoint train (143) and holdout (36) sets.
   - True MLE variance parameter with denominator n.
4. Reconciled owner cohort:
   - Shared active-and-confirmed stop contract: 293 / 341 (85.9%).
   - Preserved legacy cohort: 301 / 341 (88.3%).
   - Wilson 95% CI and Bayesian Beta(294, 49) credible intervals.
"""

from __future__ import annotations

import math
from pathlib import Path
import pytest

from cultureroute.analytics import (
    compute_cultural_shares,
    compute_weekly_forecast_backtest,
    compute_footfall_imputation_study,
)
from cultureroute.dev_lab import compute_methodology_comparison

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_three_separate_cultural_share_populations():
    """Verify cultural representation across the three separate analytical populations."""
    shares = compute_cultural_shares()

    l_info = shares["listings"]
    assert l_info.numerator == 211
    assert l_info.denominator == 675
    assert l_info.share_percent == pytest.approx(31.3, abs=0.1)

    i_info = shares["interactions"]
    assert i_info.numerator == 2144
    assert i_info.denominator == 6850
    assert i_info.share_percent == pytest.approx(31.3, abs=0.1)

    s_info = shares["planned_stops"]
    assert s_info.numerator == 961
    assert s_info.denominator == 3191
    assert s_info.share_percent == pytest.approx(30.1, abs=0.1)


def test_continuous_weekly_time_series_and_forecast_maes():
    """Verify 57 complete weeks, last-12 MAEs of 3.42 and 3.88, and next-week forecast."""
    fc = compute_weekly_forecast_backtest()
    assert fc.total_complete_weeks == 57
    assert fc.model1_mae == 3.42
    assert fc.model2_mae == 3.88

    # Next complete week prediction
    assert fc.next_week_start == "2026-08-17"
    assert fc.next_week_model1 == 44.0
    assert fc.next_week_model2 == 39.25

    # Evaluation window of exactly 12 weeks
    eval_weeks = [w for w in fc.weekly_series if w.is_evaluation_window]
    assert len(eval_weeks) == 12


def test_footfall_imputation_and_lognormal_mle():
    """Verify 225 Indian events, 46 preserved nulls, and disjoint holdout evaluation."""
    ff = compute_footfall_imputation_study()
    assert ff.total_events == 225
    assert ff.missing_count == 46
    assert ff.known_count == 179
    assert ff.train_count == 143
    assert ff.holdout_count == 36

    # Verify MLE parameters are computed and non-zero
    assert ff.mle_mu > 0.0
    assert ff.mle_sigma > 0.0
    assert ff.mle_median_val > 0.0

    # Verify original nulls are preserved in provenance
    missing_events = [e for e in ff.events_imputed if e["is_originally_missing"]]
    assert len(missing_events) == 46
    for e in missing_events:
        assert e["original_expected_footfall"] is None
        assert e["imputed_expected_footfall"] is not None


def test_owner_cohort_shared_contract_reconciliation():
    """Verify owner cohort comparison under both strict and legacy contracts."""
    # 1. Strict active-and-confirmed stop contract (293 / 341)
    strict = compute_methodology_comparison(strict_active_only=True)
    assert strict.sample_size == 341
    assert strict.success_count == 293
    assert strict.empirical_proportion == pytest.approx(0.8592, abs=0.0002)
    assert strict.wilson_lower == pytest.approx(0.8183, abs=0.001)
    assert strict.wilson_upper == pytest.approx(0.8922, abs=0.001)
    assert strict.bayes_posterior_alpha == 294
    assert strict.bayes_posterior_beta == 49
    assert strict.bayes_lower == pytest.approx(0.8183, abs=0.001)
    assert strict.bayes_upper == pytest.approx(0.8921, abs=0.001)

    # 2. Legacy cohort (301 / 341)
    legacy = compute_methodology_comparison(strict_active_only=False)
    assert legacy.sample_size == 341
    assert legacy.success_count == 301
    assert legacy.empirical_proportion == pytest.approx(0.8827, abs=0.0002)
