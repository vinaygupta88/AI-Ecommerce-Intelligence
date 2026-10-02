from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_auth_workflow():
    # 1. Test Login with Pre-Seeded Admin Account
    print("\n[*] Testing Admin Login (/api/v1/auth/login)...")
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@ecommerce.ai",
        "password": "AdminPass123!"
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_token = res.json()["access_token"]
    print(f"  [PASS] Admin authenticated. Token received: {admin_token[:20]}...")

    # 2. Test Login with Pre-Seeded Business User Account
    print("\n[*] Testing Business User Login (/api/v1/auth/login)...")
    res = client.post("/api/v1/auth/login", json={
        "email": "manager@ecommerce.ai",
        "password": "ManagerPass123!"
    })
    assert res.status_code == 200
    biz_token = res.json()["access_token"]
    print(f"  [PASS] Business user authenticated: {res.json()['role']}")

    # 3. Test Invalid Password Rejection (401)
    print("\n[*] Testing Invalid Password Handling...")
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@ecommerce.ai",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    print("  [PASS] Correctly rejected with HTTP 401 Unauthorized.")

    # 4. Test Protected Profile Endpoint (/api/v1/auth/me)
    print("\n[*] Testing Profile Inspection (/api/v1/auth/me)...")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["role"] == "admin"
    print(f"  [PASS] Profile fetched: {res.json()['full_name']} ({res.json()['email']})")

    # 5. Test Role-Based Access Control: Admin Endpoint
    print("\n[*] Testing RBAC: Admin accessing Admin endpoint (/api/v1/models/retrain)...")
    res = client.post("/api/v1/models/retrain", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    print(f"  [PASS] Admin access approved: {res.json()['status']}")

    print("\n[*] Testing RBAC: Business User accessing Admin endpoint (Expected: 403 Forbidden)...")
    res = client.post("/api/v1/models/retrain", headers={"Authorization": f"Bearer {biz_token}"})
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    print("  [PASS] Correctly blocked with HTTP 403 Forbidden.")

    print("[SUCCESS] All Authentication & RBAC assertions passed!")


if __name__ == "__main__":
    test_auth_workflow()