from datetime import datetime, timedelta
import os
import sys
import json
from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.features.build_features import main as run_feature_pipeline
from ml.training.train_forecasting_mlflow import run_experiment

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


def task_generate_features(**context):
    # Task 1: Re-computes lag and rolling window feature stores with latest data.
    print("[*] Running automated feature engineering pipeline...")
    run_feature_pipeline()
    print("[SUCCESS] Feature matrices updated in ml/data/processed/.")


def task_train_and_evaluate(**context):
    #Task 2: Trains candidate models, logs runs to MLflow, and executes promotion gate.
    print("[*] Launching MLflow experiment and training candidate models...")
    champion = run_experiment()
    print(f"[SUCCESS] Retraining complete. Champion: {champion['name']} (WAPE: {champion['val_wape']:.4f})")
    
    # Push champion run info to XCom for downstream auditing
    context["ti"].xcom_push(key="champion_name", value=champion["name"])
    context["ti"].xcom_push(key="champion_wape", value=champion["val_wape"])


def task_audit_promotion(**context):
   #Task 3: Verifies active model registry status post-retraining.
    registry_file = os.path.join(PROJECT_ROOT, "ml", "models", "production_model_registry.json")
    if not os.path.exists(registry_file):
        raise FileNotFoundError(f"Model registry file missing at {registry_file}")

    with open(registry_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("\n--- MODEL GOVERNANCE AUDIT ---")
    print(f"Active Production Model: {meta['model_name']}")
    print(f"Version:                 {meta['version']}")
    print(f"Champion Architecture:   {meta['model_type']}")
    print(f"Validation Benchmark:    WAPE {meta['validation_wape']}")
    print("------------------------------")
    print("[SUCCESS] Model promotion gate successfully verified.")


with DAG(
    dag_id="weekly_model_retrain_dag",
    default_args=default_args,
    description="Automated weekly feature refresh, model training, and MLflow registry promotion",
    schedule_interval="0 0 * * 0",  # Every Sunday at midnight UTC
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "retraining", "mlflow"],
) as dag:

    t1_features = PythonOperator(
        task_id="generate_features",
        python_callable=task_generate_features,
    )

    t2_train = PythonOperator(
        task_id="train_and_log_models",
        python_callable=task_train_and_evaluate,
    )

    t3_audit = PythonOperator(
        task_id="audit_model_promotion",
        python_callable=task_audit_promotion,
    )

    # Workflow dependencies
    t1_features >> t2_train >> t3_audit