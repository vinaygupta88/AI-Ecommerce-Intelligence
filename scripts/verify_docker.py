"""
scripts/verify_docker.py
Validates running Docker containers, internal network health, and HTTP responses.
"""

import time
import urllib.request
import json


def check_endpoint(name: str, url: str):
    print(f"[*] Checking {name} ({url})...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DockerVerifier/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
            if status == 200:
                print(f"    [PASS] {name} returned HTTP 200 OK.")
                return True
            else:
                print(f"    [FAIL] {name} returned HTTP {status}.")
                return False
    except Exception as e:
        print(f"    [FAIL] Could not connect to {name}: {e}")
        return False


def main():
    print("==================================================")
    print("DOCKER FULL-STACK CONTAINER VERIFICATION")
    print("==================================================")

    # Allow container initialization time if freshly started
    time.sleep(2)

    backend_ok = check_endpoint("FastAPI Backend Health", "http://localhost:8000/api/v1/health")
    frontend_ok = check_endpoint("Next.js Frontend UI", "http://localhost:3000")

    if backend_ok and frontend_ok:
        print("\n--------------------------------------------------")
        print("[SUCCESS] Full containerized stack is running and healthy!")
        print("  - Frontend: http://localhost:3000")
        print("  - Backend API: http://localhost:8000/docs")
        print("  - Prometheus Metrics: http://localhost:8000/metrics")
        print("--------------------------------------------------")
    else:
        print("\n[ERROR] One or more containerized services failed health checks.")
        print("Run 'docker compose logs' to inspect container failures.")


if __name__ == "__main__":
    main()
    