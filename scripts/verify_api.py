from fastapi.testclient import TestClient
from backend.app.main import app


def test_api_endpoints():
    client = TestClient(app)

    print("[*] Testing GET /api/v1/health...")
    res = client.get("/api/v1/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    print(f"    Status: {health_data['status']} | DB: {health_data['database']}")

    print("\n[*] Testing GET /api/v1/products...")
    res = client.get("/api/v1/products?limit=5")
    assert res.status_code == 200
    products = res.json()
    assert len(products) == 5
    print(f"    Retrieved {len(products)} products. First SKU: {products[0]['sku']}")

    first_id = products[0]["id"]
    print(f"\n[*] Testing GET /api/v1/products/{first_id}...")
    res = client.get(f"/api/v1/products/{first_id}")
    assert res.status_code == 200
    detail = res.json()
    print(f"    Product Name: {detail['name']} | Lead Time: {detail['lead_time_days']} days")

    print(f"\n[*] Testing ML Inference: GET /api/v1/forecast/{first_id}...")
    res = client.get(f"/api/v1/forecast/{first_id}")
    assert res.status_code == 200
    forecast = res.json()
    print(f"    Predicted 7d Demand: {forecast['predicted_demand_next_7d']} units")
    print(f"    Stockout Probability: {forecast['stockout_probability'] * 100:.1f}%")
    print(f"    Reorder Needed: {forecast['reorder_advice']['reorder_needed']}")
    print(f"    Business Explanation: {forecast['business_explanation']}")

    print("\n[*] Testing GET /api/v1/dashboard/summary...")
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    dash = res.json()
    print(f"    Total SKUs: {dash['total_skus']} | Critical SKUs: {dash['critical_stockout_skus']}")

    print("\n[SUCCESS] All FastAPI REST endpoints validated successfully!")


if __name__ == "__main__":
    test_api_endpoints()