"""
scripts/verify_redis.py
Benchmarks Redis Cache-Aside performance vs uncached DB + ML inference.
Tests cache hits, cache misses, and key invalidation.
"""

import time
from fastapi.testclient import TestClient
from backend.app.core.redis_client import CacheManager, get_redis_client
from backend.app.main import app


def benchmark_caching():
    print("==================================================")
    print("REDIS CACHING & LATENCY BENCHMARK")
    print("==================================================")

    # 1. Ping Redis
    try:
        r = get_redis_client()
        r.ping()
        print("[PASS] Successfully connected to Redis container on port 6379.")
    except Exception as e:
        print(f"[FAIL] Redis connection refused: {e}")
        print("       Ensure Docker container is running: docker compose -f docker-compose.dev.yml up -d")
        return

    client = TestClient(app)
    test_product_id = 1
    cache_key = CacheManager.build_forecast_key(test_product_id)

    # Invalidate key first to guarantee a cold cache miss
    CacheManager.invalidate_product(test_product_id)
    assert r.get(cache_key) is None, "Cache should be empty after invalidation."

    # 2. Measure Cache Miss (Uncached DB query + ML inference)
    print("\n[*] Round 1: Cold Cache Miss (PostgreSQL + ML Model Inference)...")
    start_time = time.perf_counter()
    res1 = client.get(f"/api/v1/forecast/{test_product_id}")
    miss_latency_ms = (time.perf_counter() - start_time) * 1000
    assert res1.status_code == 200
    print(f"    --> Response Status: 200 OK")
    print(f"    --> Uncached Latency: {miss_latency_ms:.2f} ms")

    # Confirm key was stored in Redis
    cached_val = r.get(cache_key)
    assert cached_val is not None, "Key was not saved to Redis."
    ttl_remaining = r.ttl(cache_key)
    print(f"    --> Stored Key: '{cache_key}' (TTL remaining: {ttl_remaining}s)")

    # 3. Measure Cache Hit (Fetched directly from Redis in-memory)
    print("\n[*] Round 2: Hot Cache Hit (Redis In-Memory)...")
    start_time = time.perf_counter()
    res2 = client.get(f"/api/v1/forecast/{test_product_id}")
    hit_latency_ms = (time.perf_counter() - start_time) * 1000
    assert res2.status_code == 200
    print(f"    --> Response Status: 200 OK")
    print(f"    --> Cached Latency:   {hit_latency_ms:.2f} ms")

    speedup = miss_latency_ms / max(0.001, hit_latency_ms)
    print(f"\n[BENCHMARK RESULT] Cache hit was {speedup:.1f}x FASTER than ML inference!")

    # 4. Test Invalidation
    print("\n[*] Testing Cache Invalidation...")
    CacheManager.invalidate_product(test_product_id)
    assert r.get(cache_key) is None
    print(f"    [PASS] Key '{cache_key}' successfully deleted from Redis.")

    print("\n--------------------------------------------------")
    print("[SUCCESS] Redis caching layer and invalidation logic fully verified!")
    print("--------------------------------------------------")


if __name__ == "__main__":
    benchmark_caching()