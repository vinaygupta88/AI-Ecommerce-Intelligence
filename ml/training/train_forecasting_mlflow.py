import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import lightgbm as lgb
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
import mlflow
import mlflow.lightgbm
import mlflow.xgboost
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.join("ml", "data", "processed")
MODELS_DIR = os.path.join("ml", "models")
EXPERIMENT_NAME = "demand_forecasting_production"
REGISTERED_MODEL_NAME = "DemandForecaster"


def calculate_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Weighted Absolute Percentage Error."""
    sum_actual = np.sum(y_true)
    if sum_actual == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / sum_actual)


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Extracts analytical features, dropping keys, dates, and target variables."""
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


def log_feature_importance(model, feature_names: list[str], output_path: str):
    """Generates and saves feature importance plot as an MLflow artifact."""
    plt.figure(figsize=(10, 6))
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        indices = np.argsort(importances)[-12:]  # Top 12 features
        plt.barh(range(len(indices)), importances[indices], align="center", color="#2563eb")
        plt.yticks(range(len(indices)), [feature_names[i] for i in indices])
        plt.xlabel("Feature Importance")
        plt.title("Top 12 Contributing Demand Drivers")
        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close()


def run_experiment():
    # Configure MLflow tracking
    tracking_uri = "sqlite:///mlruns.db"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EXPERIMENT_NAME)
    client = MlflowClient()

    logger.info("MLflow Tracking URI set to: %s", tracking_uri)
    logger.info("Active Experiment: %s", EXPERIMENT_NAME)

    # Load splits
    train_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "features_train.parquet"))
    val_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "features_val.parquet"))
    test_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "features_test.parquet"))

    features = get_feature_columns(train_df)
    target = "target_demand_next_7d"

    X_train, y_train = train_df[features], train_df[target]
    X_val, y_val = val_df[features], val_df[target]
    X_test, y_test = test_df[features], test_df[target]

    run_results = []

    # ----------------------------------------------------
    # Candidate 1: Heuristic Baseline (7-Day Moving Average)
    # ----------------------------------------------------
    with mlflow.start_run(run_name="Baseline_7d_MovingAvg") as run:
        mlflow.set_tag("model_family", "heuristic")
        mlflow.log_param("strategy", "trailing_7d_rolling_mean")
        mlflow.log_param("features_used", "rolling_mean_7")

        val_pred = val_df["rolling_mean_7"] * 7.0
        test_pred = test_df["rolling_mean_7"] * 7.0

        val_wape = calculate_wape(y_val, val_pred)
        val_mae = mean_absolute_error(y_val, val_pred)
        test_wape = calculate_wape(y_test, test_pred)

        mlflow.log_metrics({
            "val_wape": val_wape,
            "val_mae": val_mae,
            "test_wape": test_wape,
        })
        logger.info("[Baseline] Val WAPE: %.4f | Test WAPE: %.4f", val_wape, test_wape)
        run_results.append({"name": "Baseline", "val_wape": val_wape, "run_id": run.info.run_id, "model": None})

    # ----------------------------------------------------
    # Candidate 2: LightGBM Regressor
    # ----------------------------------------------------
    lgb_params = {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "verbosity": -1,
    }

    with mlflow.start_run(run_name="LightGBM_Regressor") as run:
        mlflow.set_tag("model_family", "gradient_boosting_trees")
        mlflow.set_tag("framework", "lightgbm")
        mlflow.log_params(lgb_params)
        mlflow.log_param("num_features", len(features))

        lgb_model = lgb.LGBMRegressor(**lgb_params)
        lgb_model.fit(X_train, y_train)

        val_pred = np.maximum(0, lgb_model.predict(X_val))
        test_pred = np.maximum(0, lgb_model.predict(X_test))

        val_wape = calculate_wape(y_val, val_pred)
        val_mae = float(mean_absolute_error(y_val, val_pred))
        val_rmse = float(root_mean_squared_error(y_val, val_pred))
        test_wape = calculate_wape(y_test, test_pred)

        mlflow.log_metrics({
            "val_wape": val_wape,
            "val_mae": val_mae,
            "val_rmse": val_rmse,
            "test_wape": test_wape,
        })

        # Log Feature Importance plot as artifact
        importance_plot = "lgb_feature_importance.png"
        log_feature_importance(lgb_model, features, importance_plot)
        mlflow.log_artifact(importance_plot)
        if os.path.exists(importance_plot):
            os.remove(importance_plot)

        # Log Model artifact using MLflow LightGBM flavor
        mlflow.lightgbm.log_model(
            lgb_model,
            artifact_path="model",
            registered_model_name=None,  # We register explicitly based on champion selection
        )

        logger.info("[LightGBM] Val WAPE: %.4f | Test WAPE: %.4f", val_wape, test_wape)
        run_results.append({"name": "LightGBM", "val_wape": val_wape, "run_id": run.info.run_id, "model": lgb_model})

    # ----------------------------------------------------
    # Candidate 3: XGBoost Regressor
    # ----------------------------------------------------
    xgb_params = {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "verbosity": 0,
    }

    with mlflow.start_run(run_name="XGBoost_Regressor") as run:
        mlflow.set_tag("model_family", "gradient_boosting_trees")
        mlflow.set_tag("framework", "xgboost")
        mlflow.log_params(xgb_params)
        mlflow.log_param("num_features", len(features))

        xgb_model = xgb.XGBRegressor(**xgb_params)
        xgb_model.fit(X_train, y_train)

        val_pred = np.maximum(0, xgb_model.predict(X_val))
        test_pred = np.maximum(0, xgb_model.predict(X_test))

        val_wape = calculate_wape(y_val, val_pred)
        val_mae = float(mean_absolute_error(y_val, val_pred))
        val_rmse = float(root_mean_squared_error(y_val, val_pred))
        test_wape = calculate_wape(y_test, test_pred)

        mlflow.log_metrics({
            "val_wape": val_wape,
            "val_mae": val_mae,
            "val_rmse": val_rmse,
            "test_wape": test_wape,
        })

        importance_plot = "xgb_feature_importance.png"
        log_feature_importance(xgb_model, features, importance_plot)
        mlflow.log_artifact(importance_plot)
        if os.path.exists(importance_plot):
            os.remove(importance_plot)

        mlflow.xgboost.log_model(xgb_model, artifact_path="model")

        logger.info("[XGBoost]  Val WAPE: %.4f | Test WAPE: %.4f", val_wape, test_wape)
        run_results.append({"name": "XGBoost", "val_wape": val_wape, "run_id": run.info.run_id, "model": xgb_model})

    # ----------------------------------------------------
    # Champion Selection & Governance Promotion Logic
    # ----------------------------------------------------
    # Only ML models (excluding baseline) compete for registry
    ml_candidates = [r for r in run_results if r["model"] is not None]
    champion = min(ml_candidates, key=lambda x: x["val_wape"])
    logger.info("Champion candidate identified: %s (Val WAPE: %.4f)", champion["name"], champion["val_wape"])

    # Register champion model in MLflow Model Registry
    model_uri = f"runs:/{champion['run_id']}/model"
    reg_model = mlflow.register_model(model_uri=model_uri, name=REGISTERED_MODEL_NAME)
    version = reg_model.version
    logger.info("Successfully registered %s as '%s' Version %s", champion["name"], REGISTERED_MODEL_NAME, version)

    # Promotion Gate: Tag model and assign alias/description
    client.set_model_version_tag(
        name=REGISTERED_MODEL_NAME,
        version=version,
        key="validation_wape",
        value=f"{champion['val_wape']:.4f}",
    )
    client.set_registered_model_alias(
        name=REGISTERED_MODEL_NAME,
        alias="champion",
        version=version,
    )

    client.update_model_version(
        name=REGISTERED_MODEL_NAME,
        version=version,
        description=f"Champion {champion['name']} model selected automatically. Validation WAPE: {champion['val_wape']:.4f}",
    )

    logger.info("[PROMOTION SUCCESS] %s Version %s promoted with alias '@champion'", REGISTERED_MODEL_NAME, version)

    # Save local metadata reference for FastAPI serving parity
    local_meta = {
        "model_name": REGISTERED_MODEL_NAME,
        "version": version,
        "run_id": champion["run_id"],
        "model_type": champion["name"],
        "validation_wape": round(champion["val_wape"], 4),
        "tracking_uri": tracking_uri,
    }
    with open(os.path.join(MODELS_DIR, "production_model_registry.json"), "w", encoding="utf-8") as f:
        json.dump(local_meta, f, indent=2)

    return champion


if __name__ == "__main__":
    run_experiment()