"""Unit and Integration Tests for Stage P6: Supervised Prediction Model.

Verifies:
1. Panel construction: 45 cities x 57 complete weeks = 2,565 rows, 2,138 qualifying actions, 1,191 zero-count city-weeks.
2. Feature engineering: lag_1, lag_2, trailing_4w_mean strictly past-only; 2,385 eligible rows after 4-week initialization.
3. Chronological time partitioning: 1,845 train rows (Weeks 5..45) and 540 holdout test rows (Weeks 46..57).
4. Supervised PoissonRegressor fitting: non-negative predictions, out-of-sample MAE/RMSE calculation vs baselines.
5. Dated prediction for week 2026-08-17: 45 cities projected with Poisson 95% confidence intervals.
6. Artifact persistence: models/poisson_model_artifact.json contains metadata, parameters, metrics, predictions.
7. Streamlit integration: AppTest renders Prediction Model view without errors.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from cultureroute.prediction_model import (
    ARTIFACT_PATH,
    build_city_week_panel,
    train_and_evaluate_poisson_model,
    load_model_artifact,
)


def test_panel_construction_dimensions():
    """Verify panel shape, cities, complete weeks, qualifying interactions, and zero-count sparsity."""
    dataset = build_city_week_panel()

    assert dataset.total_cities == 45, f"Expected 45 study cities, got {dataset.total_cities}"
    assert dataset.total_weeks == 57, f"Expected 57 complete weeks, got {dataset.total_weeks}"
    assert dataset.total_panel_rows == 2565, f"Expected 2,565 rows (45x57), got {dataset.total_panel_rows}"
    assert dataset.qualifying_actions == 2138, f"Expected 2,138 qualifying actions, got {dataset.qualifying_actions}"
    assert dataset.zero_count_rows == 1191, f"Expected 1,191 zero-count city-weeks, got {dataset.zero_count_rows}"


def test_feature_engineering_and_no_leakage():
    """Verify strictly past-only lag features and initialization drop count."""
    dataset = build_city_week_panel()
    eligible = dataset.eligible_df

    # First 4 weeks per city dropped: 45 * 4 = 180 dropped -> 2,565 - 180 = 2,385
    assert len(eligible) == 2385, f"Expected 2,385 eligible rows, got {len(eligible)}"

    # Check a specific city: Jaipur
    jaipur_df = eligible[eligible["city_name"] == "Jaipur"].sort_values("week_date").reset_index(drop=True)
    assert len(jaipur_df) == 53  # 57 - 4 = 53 weeks

    # Verify lag_1 matches previous week's interaction count exactly
    full_jaipur = dataset.panel_df[dataset.panel_df["city_name"] == "Jaipur"].sort_values("week_date").reset_index(drop=True)
    for idx in range(4, len(full_jaipur)):
        w_start = full_jaipur.loc[idx, "week_start"]
        row_elig = jaipur_df[jaipur_df["week_start"] == w_start]
        assert not row_elig.empty
        # lag_1 should equal full_jaipur count at idx - 1
        expected_lag1 = full_jaipur.loc[idx - 1, "interaction_count"]
        actual_lag1 = row_elig["lag_1"].values[0]
        assert actual_lag1 == expected_lag1, f"Lag 1 mismatch at {w_start}: {actual_lag1} vs {expected_lag1}"

        # trailing_4w_mean should equal mean of idx-4..idx-1
        expected_4w = full_jaipur.loc[idx-4:idx-1, "interaction_count"].mean()
        actual_4w = row_elig["trailing_4w_mean"].values[0]
        assert abs(actual_4w - expected_4w) < 1e-6, f"4W mean mismatch at {w_start}"


def test_chronological_split_properties():
    """Verify train/test split has whole-week partitioning and no future leakage."""
    dataset = build_city_week_panel()

    assert dataset.train_rows == 1845, f"Expected 1,845 train rows, got {dataset.train_rows}"
    assert dataset.test_rows == 540, f"Expected 540 test rows, got {dataset.test_rows}"
    assert dataset.train_rows + dataset.test_rows == 2385

    train_weeks = set(dataset.train_df["week_start"].unique())
    test_weeks = set(dataset.test_df["week_start"].unique())

    # Strictly disjoint
    assert len(train_weeks.intersection(test_weeks)) == 0, "Train and test weeks must be strictly disjoint"
    assert len(train_weeks) == 41, f"Expected 41 train weeks, got {len(train_weeks)}"
    assert len(test_weeks) == 12, f"Expected 12 holdout test weeks, got {len(test_weeks)}"

    # Train max date strictly before test min date
    max_train_date = max(dataset.train_df["week_date"])
    min_test_date = min(dataset.test_df["week_date"])
    assert max_train_date < min_test_date, f"Leakage detected: train {max_train_date} >= test {min_test_date}"


def test_poisson_regressor_training_and_metrics():
    """Verify PoissonRegressor fitting, nonnegativity, and expected error ranges."""
    eval_result, dated_result, pipeline = train_and_evaluate_poisson_model(alpha=1.0, save_artifact=False)

    assert eval_result.train_rows == 1845
    assert eval_result.test_rows == 540
    assert eval_result.test_weeks_count == 12

    # Check non-negative predictions
    test_preds = eval_result.test_predictions_df["y_pred"].values
    assert np.all(test_preds >= 0.0), "Poisson predictions must be strictly non-negative"

    # Check MAE values (Poisson model ~ 0.79 interactions/city-week)
    assert 0.70 < eval_result.model_mae < 0.90, f"Unexpected model MAE: {eval_result.model_mae}"
    assert 0.85 < eval_result.baseline_prev_mae < 1.05, f"Unexpected base prev MAE: {eval_result.baseline_prev_mae}"
    assert 0.70 < eval_result.baseline_4w_mae < 0.90, f"Unexpected base 4W MAE: {eval_result.baseline_4w_mae}"

    # Verify model beats previous-week baseline
    assert eval_result.model_mae < eval_result.baseline_prev_mae, "Poisson model must beat previous-week baseline"

    # Verify stratified target counts
    assert eval_result.zero_targets_count == 264
    assert eval_result.nonzero_targets_count == 276
    assert eval_result.zero_targets_count + eval_result.nonzero_targets_count == 540


def test_dated_prediction_for_target_week():
    """Verify dated prediction for week 2026-08-17 across all 45 cities."""
    eval_result, dated_result, pipeline = train_and_evaluate_poisson_model(alpha=1.0, save_artifact=False)

    assert dated_result.target_week_start == "2026-08-17"
    assert dated_result.snapshot_cutoff == "2026-08-16"
    assert len(dated_result.city_predictions) == 45

    # Check confidence intervals: ci_lower <= predicted <= ci_upper
    for cp in dated_result.city_predictions:
        assert cp["ci_lower_95"] <= cp["predicted_interactions"] <= cp["ci_upper_95"]
        assert cp["ci_lower_95"] >= 0.0

    # Total predicted across India is around 38 interactions
    assert 30.0 < dated_result.total_predicted_interactions < 45.0, (
        f"Unexpected total prediction: {dated_result.total_predicted_interactions}"
    )


def test_artifact_persistence_and_loading():
    """Verify JSON artifact structure, metadata, parameters, and reloadability."""
    # Ensure artifact exists by saving
    train_and_evaluate_poisson_model(alpha=1.0, save_artifact=True)
    assert ARTIFACT_PATH.exists()

    artifact = load_model_artifact()
    assert artifact is not None
    assert "metadata" in artifact
    assert "model_parameters" in artifact
    assert "metrics" in artifact
    assert "dated_prediction_2026_08_17" in artifact

    meta = artifact["metadata"]
    assert meta["model_family"] == "sklearn.linear_model.PoissonRegressor"
    assert meta["study_cities"] == 45
    assert meta["complete_weeks"] == 57
    assert meta["panel_total_rows"] == 2565
    assert meta["train_rows"] == 1845
    assert meta["test_rows"] == 540


def test_model_view_in_apptest():
    """Verify Streamlit AppTest renders Prediction Model screen (?view=model)."""
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parent.parent / "app.py"
    at = AppTest.from_file(str(app_path), default_timeout=25)
    at.query_params["view"] = "model"
    at.run()

    assert not at.exception
    # Verify headings and tabs render
    markdown_texts = [m.value for m in at.markdown]
    has_title = any("Cultural Engagement" in t and "Prediction Model" in t for t in markdown_texts)
    assert has_title, "Prediction Model title not found in rendered output"
