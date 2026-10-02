import mlflow
from mlflow.tracking import MlflowClient

EXPERIMENT_NAME = "demand_forecasting_production"
REGISTERED_MODEL_NAME = "DemandForecaster"


def verify_mlflow():
    tracking_uri = "sqlite:///mlruns.db"
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    print("[*] Connecting to MLflow Tracking Server...")
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    assert experiment is not None, f"Experiment '{EXPERIMENT_NAME}' not found."
    print(f"    Experiment Found: '{experiment.name}' (ID: {experiment.experiment_id})")

    # Verify Runs
    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    print(f"    Total Runs Logged: {len(runs)}")
    assert len(runs) >= 3, "Expected at least 3 runs (Baseline, LightGBM, XGBoost)."

    for run in runs:
        run_name = run.data.tags.get("mlflow.runName", "Unnamed")
        wape = run.data.metrics.get("val_wape", "N/A")
        print(f"      - Run: {run_name:<22} | Val WAPE: {wape}")

    # Verify Model Registry
    print("\n[*] Checking MLflow Model Registry...")
    reg_model = client.get_registered_model(REGISTERED_MODEL_NAME)
    assert reg_model is not None, f"Registered model '{REGISTERED_MODEL_NAME}' not found."

    # Check alias
    champion_version = client.get_model_version_by_alias(REGISTERED_MODEL_NAME, "champion")
    print(f"    Registered Model: '{reg_model.name}'")
    print(f"    Champion Alias Points to Version: {champion_version.version}")
    print(f"    Source Run ID: {champion_version.run_id}")
    print(f"    Description: {champion_version.description}")

    print("\n[SUCCESS] MLflow Experiment Tracking & Model Registry fully verified!")


if __name__ == "__main__":
    verify_mlflow()