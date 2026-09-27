import os
import json
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.join("ml", "data", "processed")
MODELS_DIR = os.path.join("ml", "models")


def train_anomaly_detector():
    logger.info("Training Isolation Forest on sales patterns...")
    train_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "features_train.parquet"))

    # Anomaly features: sales volume, velocity ratio, price, and volatility
    anomaly_features = [
        "total_units_sold",
        "sales_velocity_ratio",
        "rolling_std_7",
        "base_price",
        "discount_pct",
    ]

    X_train = train_df[anomaly_features].fillna(0)

    # Contamination set to 3% based on expected tail sales shocks
    iso = IsolationForest(
        n_estimators=150,
        contamination=0.03,
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X_train)

    artifact_path = os.path.join(MODELS_DIR, "anomaly_detector.joblib")
    joblib.dump(iso, artifact_path)

    metadata = {
        "model_type": "IsolationForest",
        "task": "sales_anomaly_detection",
        "contamination": 0.03,
        "features": anomaly_features,
    }
    with open(os.path.join(MODELS_DIR, "anomaly_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Anomaly detector saved to %s", artifact_path)


if __name__ == "__main__":
    train_anomaly_detector()