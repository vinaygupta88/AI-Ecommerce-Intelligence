import os
import json
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.join("ml", "data", "processed")
MODELS_DIR = os.path.join("ml", "models")


def calculate_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Weighted Absolute Percentage Error (WAPE = sum(|y - y_hat|) / sum(y))."""
    sum_actual = np.sum(y_true)
    if sum_actual == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / sum_actual)


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Isolates numerical feature columns, excluding identifiers, dates, and targets."""
    ignore_cols = {
        "date",
        "product_id",
        "sku",
        "name",
        "total_revenue",
        "unfulfilled_demand",
        "target_demand_next_7d",
        "target_stockout_leadtime",
    }
    return [col for col in df.columns if col not in ignore_cols]


def train_forecasting_models():
    logger.info("Loading train and validation datasets...")
    train_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "features_train.parquet"))
    val_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "features_val.parquet"))

    features = get_feature_columns(train_df)
    target = "target_demand_next_7d"

    X_train, y_train = train_df[features], train_df[target]
    X_val, y_val = val_df[features], val_df[target]

    logger.info("Training features count: %d. Training rows: %d.", len(features), len(X_train))

    # 1. Baseline Model: 7-Day Trailing Average Scaled to 7-Day Horizon
    # If a product sold 20 units/day over the last 7 days, baseline predicts 20 * 7 = 140 units.
    baseline_pred = val_df["rolling_mean_7"] * 7.0
    baseline_wape = calculate_wape(y_val, baseline_pred)
    baseline_mae = mean_absolute_error(y_val, baseline_pred)
    logger.info("--> Baseline (7d Moving Avg) | Val WAPE: %.4f | Val MAE: %.2f", baseline_wape, baseline_mae)

    # 2. LightGBM Regressor
    lgb_model = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )
    lgb_model.fit(X_train, y_train)
    lgb_val_pred = np.maximum(0, lgb_model.predict(X_val))
    lgb_wape = calculate_wape(y_val, lgb_val_pred)
    lgb_mae = mean_absolute_error(y_val, lgb_val_pred)
    logger.info("--> LightGBM Regressor       | Val WAPE: %.4f | Val MAE: %.2f", lgb_wape, lgb_mae)

    # 3. XGBoost Regressor
    xgb_model = xgb.XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    xgb_model.fit(X_train, y_train)
    xgb_val_pred = np.maximum(0, xgb_model.predict(X_val))
    xgb_wape = calculate_wape(y_val, xgb_val_pred)
    xgb_mae = mean_absolute_error(y_val, xgb_val_pred)
    logger.info("--> XGBoost Regressor        | Val WAPE: %.4f | Val MAE: %.2f", xgb_wape, xgb_mae)

    # Champion Selection
    candidates = [
        {"name": "LightGBM", "model": lgb_model, "wape": lgb_wape, "mae": lgb_mae},
        {"name": "XGBoost", "model": xgb_model, "wape": xgb_wape, "mae": xgb_mae},
    ]
    champion = min(candidates, key=lambda x: x["wape"])
    logger.info("Selected Champion: %s with WAPE: %.4f (vs Baseline: %.4f)", champion["name"], champion["wape"], baseline_wape)

    # Save Model Artifact
    artifact_path = os.path.join(MODELS_DIR, "demand_forecaster.joblib")
    joblib.dump(champion["model"], artifact_path)

    # Save Metadata & Feature List for Inference Validation
    metadata = {
        "model_type": champion["name"],
        "task": "demand_forecasting_7d",
        "validation_wape": round(champion["wape"], 4),
        "validation_mae": round(champion["mae"], 2),
        "baseline_wape": round(baseline_wape, 4),
        "feature_names": features,
    }
    with open(os.path.join(MODELS_DIR, "forecasting_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Forecaster artifact saved to %s", artifact_path)
    return champion


if __name__ == "__main__":
    train_forecasting_models()