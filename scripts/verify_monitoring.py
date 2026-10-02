"""
scripts/verify_monitoring.py
Validates Evidently AI drift detection output and scrapes Prometheus metrics from FastAPI.
"""

import os
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from monitoring.evidently.drift_monitor import run_drift_analysis


def test_monitoring_stack():
    print("==================================================")
    print("OBSERVABILITY & MONITORING VERIFICATION")
    print("==================================================")

    # 1. Test Evidently Drift Monitoring
    print("[*] Executing Evidently AI Drift Detection Pipeline...")
    summary = run_drift_analysis()

    assert os.path.exists("monitoring/drift_report.html"), "HTML drift report not found."
    assert os.path.exists("monitoring/drift_metrics.json"), "JSON drift metrics not found."
    assert "dataset_drift_detected" in summary
    assert "total_features_evaluated" in summary
    assert summary["total_features_evaluated"] == 10
    print("[PASS] Evidently AI Data Drift artifacts created and validated.")

    # 2. Test Prometheus Instrumentation on FastAPI
    print("\n[*] Testing Prometheus /metrics Endpoint on FastAPI...")
    client = TestClient(app)

    # Generate test traffic
    client.get("/api/v1/health")
    client.get("/api/v1/products?limit=2")
    client.get("/api/v1/dashboard/summary")

    # Scrape Prometheus metrics
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200, f"Prometheus endpoint failed: {metrics_res.text}"
    metrics_text = metrics_res.text

    print(f"    --> Response Status: 200 OK")
    print(f"    --> Payload Length:  {len(metrics_text)} bytes")

    # Assert standard Prometheus metric keys exist
    expected_metrics = [
        "http_requests_total",
        "http_request_duration_seconds",
    ]
    for metric in expected_metrics:
        assert metric in metrics_text, f"Missing expected metric: {metric}"
        print(f"    [OK] Metric exposed: {metric}")

    print("\n--------------------------------------------------")
    print("[SUCCESS] Evidently AI Drift & Prometheus metrics verified successfully!")
    print("--------------------------------------------------")


if __name__ == "__main__":
    test_monitoring_stack()