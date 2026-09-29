import os
import json
import pandas as pd
import numpy as np
import logging
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "processed")
OUTPUT_HTML = os.path.join(PROJECT_ROOT, "monitoring", "drift_report.html")
OUTPUT_JSON = os.path.join(PROJECT_ROOT, "monitoring", "drift_metrics.json")


def load_drift_datasets() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Loads baseline training features and current production evaluation features."""
    train_path = os.path.join(PROCESSED_DIR, "features_train.parquet")
    test_path = os.path.join(PROCESSED_DIR, "features_test.parquet")

    if not os.path.exists(train_path) or not os.path.exists(test_path):
        raise FileNotFoundError("Feature parquets missing. Run Phase 4 first.")

    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)

    monitored_features = [
        "base_price",
        "lead_time_days",
        "closing_stock",
        "total_units_sold",
        "sales_velocity_ratio",
        "rolling_mean_7",
        "rolling_std_7",
        "rolling_mean_30",
        "promotional_flag",
        "discount_pct",
    ]

    return train_df[monitored_features], test_df[monitored_features], monitored_features


def run_drift_analysis():
    logger.info("Initializing Evidently AI Drift Monitoring...")
    ref_df, curr_df, features = load_drift_datasets()

    logger.info("Reference data (Train): %d rows | Current data (Prod): %d rows", len(ref_df), len(curr_df))

    # Initialize Evidently Report
    report = Report(metrics=[
        DataDriftPreset(),
    ])

    report.run(reference_data=ref_df, current_data=curr_df)

    # 1. Save Interactive HTML Report
    report.save_html(OUTPUT_HTML)
    logger.info("Interactive HTML drift report saved: %s", OUTPUT_HTML)

    # 2. Extract Metrics safely across Evidently dictionary structures
    raw_dict = report.as_dict()
    metrics_list = raw_dict.get("metrics", [])

    # Find the data drift metric container
    drift_result = {}
    for m in metrics_list:
        res = m.get("result", {})
        if "number_of_columns" in res or "number_of_drifted_columns" in res or "drift_by_columns" in res:
            drift_result = res
            break

    if not drift_result and len(metrics_list) > 0:
        drift_result = metrics_list[0].get("result", {})

    number_of_features = drift_result.get("number_of_columns", len(features))
    drifted_features_count = drift_result.get("number_of_drifted_columns", 0)
    share_of_drifted = drift_result.get("share_of_drifted_columns", 0.0)
    dataset_drift_detected = drift_result.get("dataset_drift", False)

    # Safely extract column-level drift information
    cols_data = drift_result.get("drift_by_columns", {})
    feature_details = {}

    for col in features:
        col_info = cols_data.get(col, {})
        drift_flag = bool(col_info.get("drift_detected", False))
        p_val = col_info.get("drift_score", None)
        if p_val is None:
            p_val = 1.0
        stat_name = col_info.get("stattest_name", "kolmogorov_smirnov")

        feature_details[col] = {
            "drift_detected": drift_flag,
            "drift_score_p_value": round(float(p_val), 5),
            "stat_test": str(stat_name),
            "current_mean": round(float(curr_df[col].mean()), 2),
            "reference_mean": round(float(ref_df[col].mean()), 2),
        }

    # 3. Create Operational Summary
    summary = {
        "dataset_drift_detected": bool(dataset_drift_detected),
        "total_features_evaluated": int(number_of_features),
        "drifted_features_count": int(drifted_features_count),
        "share_of_drifted_columns": round(float(share_of_drifted), 4),
        "action_required": "INVESTIGATE_AND_RETRAIN" if dataset_drift_detected else "NORMAL_OPERATION",
        "feature_drift_details": feature_details,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("Drift summary metadata saved: %s", OUTPUT_JSON)

    print("\n==================================================")
    print("EVIDENTLY AI DRIFT DETECTION RESULTS")
    print("==================================================")
    print(f"Dataset Drift Flag:      {'[DRIFT DETECTED]' if dataset_drift_detected else '[NO SIGNIFICANT DRIFT]'}")
    print(f"Drifted Features:        {drifted_features_count} / {number_of_features} ({share_of_drifted * 100:.1f}%)")
    print(f"Recommended Action:      {summary['action_required']}")
    print("\nFeature Drift Breakdown:")
    for feat, data in feature_details.items():
        status_tag = "[DRIFT]" if data["drift_detected"] else "[OK]   "
        print(f"  {status_tag} {feat:<22} | p-val: {data['drift_score_p_value']:<7} | Ref Mean: {data['reference_mean']:<7} | Curr Mean: {data['current_mean']}")
    print("==================================================\n")

    return summary


if __name__ == "__main__":
    run_drift_analysis()