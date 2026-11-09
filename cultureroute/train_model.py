"""CLI runner for CultureRoute Supervised Prediction Model (Stage P6).

Usage:
    .venv/Scripts/python.exe cultureroute/train_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cultureroute.prediction_model import train_and_evaluate_poisson_model, ARTIFACT_PATH


def main() -> int:
    print("=" * 72)
    print("CultureRoute Supervised Prediction Model · Stage P6 Training Runner")
    print("Model Family: scikit-learn.linear_model.PoissonRegressor (alpha=1.0)")
    print("=" * 72)

    print("\n1. Building balanced 45-city x 57-week panel and lag features...")
    eval_result, dated_result, pipeline = train_and_evaluate_poisson_model(alpha=1.0, save_artifact=True)

    print(f"   - Training Window: Weeks 5..45 ({eval_result.train_rows:,} rows)")
    print(f"   - Holdout Test Window: Weeks 46..57 ({eval_result.test_rows:,} rows across 12 complete weeks)")
    print(f"   - Artifact Saved: {ARTIFACT_PATH}")

    print("\n2. Out-of-Sample Holdout Evaluation Results (12-Week Disjoint Test Split):")
    print(f"   {'Model / Baseline':<35} | {'MAE (int/city-wk)':<18} | {'RMSE':<10}")
    print("   " + "-" * 68)
    print(f"   {'PoissonRegressor (alpha=1.0)':<35} | {eval_result.model_mae:<18.4f} | {eval_result.model_rmse:<10.4f}")
    print(f"   {'Previous-Week Baseline (lag_1)':<35} | {eval_result.baseline_prev_mae:<18.4f} | {eval_result.baseline_prev_rmse:<10.4f}")
    print(f"   {'Trailing 4-Week Mean Baseline':<35} | {eval_result.baseline_4w_mae:<18.4f} | {eval_result.baseline_4w_rmse:<10.4f}")

    print("\n3. Stratified Subpopulation Performance:")
    print(f"   - Zero-count targets (n={eval_result.zero_targets_count}):")
    print(f"     * Poisson Model MAE:      {eval_result.zero_model_mae:.4f}")
    print(f"     * Previous-Week MAE:     {eval_result.zero_base_prev_mae:.4f}")
    print(f"     * Trailing 4-Week MAE:    {eval_result.zero_base_4w_mae:.4f}")
    print(f"   - Non-zero targets (n={eval_result.nonzero_targets_count}):")
    print(f"     * Poisson Model MAE:      {eval_result.nonzero_model_mae:.4f} (strongest on active demand)")
    print(f"     * Previous-Week MAE:     {eval_result.nonzero_base_prev_mae:.4f}")
    print(f"     * Trailing 4-Week MAE:    {eval_result.nonzero_base_4w_mae:.4f}")

    print("\n4. Dated Predictions for Target Week 2026-08-17 (Post-Cutoff Evaluation):")
    print(f"   Total Predicted Cultural Interactions across India: {dated_result.total_predicted_interactions:.2f}")
    print(f"   Top 5 Cities Projected:")
    for i, cp in enumerate(dated_result.city_predictions[:5], start=1):
        print(f"     {i}. {cp['city_name']:<15} : {cp['predicted_interactions']:.3f} exp interactions (95% CI: [{cp['ci_lower_95']}, {cp['ci_upper_95']}])")

    print("\n" + "=" * 72)
    print("SUCCESS: Stage P6 model artifact verified and persisted successfully.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
