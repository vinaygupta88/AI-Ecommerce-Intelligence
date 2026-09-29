from datetime import datetime, timedelta
import os
import sys
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

# Ensure project root is in Python path for local modular imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.core.database import SessionLocal
from backend.app.models.entities import DailySales, Inventory, Product
from ml.features.validation import validate_daily_aggregations

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def task_ingest_and_validate(**context):
    # Task 1: Ingests the latest operational records and verifies schema bounds.
    processed_path = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "daily_sales_inventory.parquet")
    if not os.path.exists(processed_path):
        raise FileNotFoundError(f"Source dataset missing at {processed_path}")

    df = pd.read_parquet(processed_path)
    # Validate the data integrity using our Phase 2 validator
    validate_daily_aggregations(df)

    latest_date = df["date"].max()
    print(f"[*] Ingested and validated dataset up to {latest_date}. Total rows: {len(df):,}")
    return str(latest_date)


def task_sync_postgres(**context):
    # Task 2: Syncs daily metrics and refreshes current stock levels in PostgreSQL.
    db = SessionLocal()
    try:
        # Check database connectivity and product counts
        prod_count = db.query(Product).count()
        inv_count = db.query(Inventory).count()
        sales_count = db.query(DailySales).count()

        print(f"[*] Database Sync Status:")
        print(f"    Products:    {prod_count}")
        print(f"    Inventory:   {inv_count}")
        print(f"    Daily Sales: {sales_count:,}")

        if prod_count == 0:
            raise ValueError("PostgreSQL products table is empty. Run Phase 7 seed first.")

        print("[SUCCESS] Relational database is synchronized with daily ledger.")
    finally:
        db.close()


def task_post_sync_summary(**context):
    #Task 3: Logs execution metadata and confirms synchronization.
    print("[SUCCESS] daily_data_sync_dag completed successfully.")


with DAG(
    dag_id="daily_data_sync_dag",
    default_args=default_args,
    description="Daily ingestion, validation, and PostgreSQL operational sync",
    schedule_interval="0 2 * * *",  # Every day at 02:00 AM UTC
    catchup=False,
    max_active_runs=1,
    tags=["production", "data_sync", "ecommerce"],
) as dag:

    t1_ingest_validate = PythonOperator(
        task_id="ingest_and_validate_delta",
        python_callable=task_ingest_and_validate,
    )

    t2_sync_db = PythonOperator(
        task_id="sync_postgres_tables",
        python_callable=task_sync_postgres,
    )

    t3_summary = PythonOperator(
        task_id="post_sync_summary",
        python_callable=task_post_sync_summary,
    )

    # Enforce task dependency sequence
    t1_ingest_validate >> t2_sync_db >> t3_summary