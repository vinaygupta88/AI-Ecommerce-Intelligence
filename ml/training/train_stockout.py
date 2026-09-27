import os
import json
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.join("ml", "data", "processed")
MODELS_DIR = os.path.join("ml", "models")


def train_stockout_model():
    logger.info("Loading feature splits for stockout classification...")
    train_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "features_train.parquet"))
    val_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "features_val.parquet"))

    with open(os.path.join(MODELS_DIR, "forecasting_metadata.json"), "r", encoding="utf-8") as f:
        features = json.load(f)["feature_names"]

    target = "target_stockout_leadtime"
    X_train, y_train = train_df[features], train_df[target]
    X_val, y_val = val_df[features], val_df[target]

    # Calculate class weight ratio: negative_count / positive_count
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    pos_weight = float(neg_count / pos_count) if pos_count > 0 else 1.0
    logger.info("Train class balance: Negatives=%d, Positives=%d (scale_pos_weight=%.2f)", neg_count, pos_count, pos_weight)

    clf = xgb.XGBClassifier(
        n_estimators=250,
        learning_rate=0.04,
        max_depth=5,
        scale_pos_weight=pos_weight,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
    )
    clf.fit(X_train, y_train)

    val_probs = clf.predict_proba(X_val)[:, 1]
    val_preds = (val_probs >= 0.5).astype(int)

    roc_auc = roc_auc_score(y_val, val_probs)
    pr_auc = average_precision_score(y_val, val_probs)
    logger.info("Validation ROC-AUC: %.4f | PR-AUC: %.4f", roc_auc, pr_auc)
    print("\nStockout Classification Report (Validation):")
    print(classification_report(y_val, val_preds, target_names=["In-Stock", "Stockout"]))

    # Save Artifact
    artifact_path = os.path.join(MODELS_DIR, "stockout_classifier.joblib")
    joblib.dump(clf, artifact_path)

    metadata = {
        "model_type": "XGBClassifier",
        "task": "stockout_classification_leadtime",
        "validation_roc_auc": round(float(roc_auc), 4),
        "validation_pr_auc": round(float(pr_auc), 4),
        "scale_pos_weight": round(pos_weight, 2),
        "feature_names": features,
    }
    with open(os.path.join(MODELS_DIR, "stockout_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Stockout classifier artifact saved to %s", artifact_path)


if __name__ == "__main__":
    train_stockout_model()