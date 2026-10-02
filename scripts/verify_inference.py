import os
import json
import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml.inference.predictor import InferenceService

from ml.inference.predictor import InferenceService


def test_inference_pipeline():
    print("Testing InferenceService...")
    service = InferenceService()

    # Load 1 sample row from holdout test set
    test_df = pd.read_parquet(os.path.join("ml", "data", "processed", "features_test.parquet"))
    sample_row = test_df.iloc[42]

    sku_id = sample_row.get("product_id", "Unknown")
    date_val = sample_row.get("date", "Unknown")
    actual_stock = sample_row.get("closing_stock", 0)

    print(f"Running inference for Product ID: {sku_id} on Date: {date_val} (Current Stock: {actual_stock})")
    result = service.predict_sku_state(sample_row)

    print("\n--- INFERENCE SERVICE RESPONSE ---")
    print(json.dumps(result, indent=2))
    print("-----------------------------------")

    assert "predicted_demand_next_7d" in result
    assert "stockout_probability" in result
    assert "reorder_advice" in result
    assert result["predicted_demand_next_7d"] >= 0
    assert 0.0 <= result["stockout_probability"] <= 1.0

    print("[SUCCESS] InferenceService returned valid real-world predictions.")


if __name__ == "__main__":
    test_inference_pipeline()