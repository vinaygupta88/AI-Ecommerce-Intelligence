"""
tests/conftest.py
Global pytest fixtures shared across unit and integration test suites.
"""

import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture(scope="session")
def api_client():
    """Yields a FastAPI TestClient instance for integration tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_feature_series():
    """Provides a synthetic single-SKU feature vector matching model schema."""
    return pd.Series({
        "base_price": 49.99,
        "lead_time_days": 7,
        "reorder_point": 120,
        "target_stock": 300,
        "closing_stock": 85,
        "total_units_sold": 22,
        "promotional_flag": 0,
        "discount_pct": 0.0,
        "stockout_flag": 0,
        "sales_lag_1": 20,
        "sales_lag_2": 18,
        "sales_lag_7": 25,
        "sales_lag_14": 21,
        "sales_lag_21": 19,
        "sales_lag_30": 22,
        "rolling_mean_7": 21.4,
        "rolling_std_7": 3.8,
        "rolling_max_7": 28,
        "rolling_mean_30": 20.1,
        "rolling_std_30": 4.1,
        "sales_velocity_ratio": 1.06,
        "dow_sin": 0.7818,
        "dow_cos": 0.6234,
        "month_sin": 0.5,
        "month_cos": 0.866,
        "is_weekend": 0,
        "cat_Apparel": 1,
        "cat_Beauty & Health": 0,
        "cat_Electronics": 0,
        "cat_Fitness & Outdoors": 0,
        "cat_Home & Kitchen": 0,
    })


@pytest.fixture
def invalid_raw_transactions_df():
    """Constructs a DataFrame violating schema constraints for testing validation."""
    return pd.DataFrame([
        {
            "order_id": 101,
            "product_id": 1,
            "date": "2024-01-01",
            "quantity": -5,         # INVALID: negative quantity
            "unit_price": 25.0,
            "discount": 0.1,
        },
        {
            "order_id": 102,
            "product_id": None,      # INVALID: null product identifier
            "date": "2024-01-01",
            "quantity": 2,
            "unit_price": -10.0,     # INVALID: negative price
            "discount": 1.5,         # INVALID: discount > 100%
        },
    ])