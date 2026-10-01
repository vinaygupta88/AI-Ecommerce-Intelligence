"""
tests/integration/test_api_endpoints.py
Integration tests validating FastAPI REST API endpoints, status codes, and schema validation.
"""


def test_healthcheck_endpoint(api_client):
    res = api_client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "ml_models" in data


def test_product_catalog_pagination(api_client):
    res = api_client.get("/api/v1/products?skip=0&limit=10")
    assert res.status_code == 200
    products = res.json()
    assert isinstance(products, list)
    assert len(products) <= 10
    if len(products) > 0:
        p = products[0]
        assert "sku" in p
        assert "current_stock" in p
        assert p["stock_status"] in ["NORMAL", "LOW", "CRITICAL"]


def test_get_nonexistent_product_returns_404(api_client):
    res = api_client.get("/api/v1/products/999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_forecast_endpoint_returns_valid_prediction(api_client):
    # Product 1 is guaranteed seeded
    res = api_client.get("/api/v1/forecast/1")
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == 1
    assert data["predicted_demand_next_7d"] >= 0.0
    assert 0.0 <= data["stockout_probability"] <= 1.0
    assert isinstance(data["reorder_advice"], dict)
    assert "suggested_reorder_qty" in data["reorder_advice"]
    assert len(data["business_explanation"]) > 0


def test_dashboard_summary_kpis(api_client):
    res = api_client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_skus"] >= 1
    assert summary["total_inventory_units"] >= 0
    assert isinstance(summary["top_risk_products"], list)


def test_invalid_query_parameter_fails_pydantic_validation(api_client):
    # limit must be between 1 and 100 according to schemas
    res = api_client.get("/api/v1/products?limit=500")
    assert res.status_code == 422  # Unprocessable Entity
    