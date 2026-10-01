"""
tests/unit/test_data_validation.py
Unit tests verifying strict data assertions and boundary condition handling.
"""

import pytest
import pandas as pd
from ml.features.validation import (
    validate_raw_transactions,
    validate_daily_aggregations,
    DataValidationError,
)


def test_valid_transactions_pass():
    valid_df = pd.DataFrame([{
        "order_id": 1001,
        "product_id": 1,
        "date": "2024-05-01",
        "quantity": 3,
        "unit_price": 29.99,
        "discount": 0.15,
    }])
    assert validate_raw_transactions(valid_df) is True


def test_negative_quantity_raises_validation_error():
    bad_df = pd.DataFrame([{
        "order_id": 1002,
        "product_id": 1,
        "date": "2024-05-01",
        "quantity": -1,
        "unit_price": 20.0,
        "discount": 0.0,
    }])
    with pytest.raises(DataValidationError, match="quantity <= 0"):
        validate_raw_transactions(bad_df)


def test_null_identifiers_raise_validation_error():
    bad_df = pd.DataFrame([{
        "order_id": None,
        "product_id": 1,
        "date": "2024-05-01",
        "quantity": 2,
        "unit_price": 15.0,
        "discount": 0.0,
    }])
    with pytest.raises(DataValidationError, match="null values in order_id or product_id"):
        validate_raw_transactions(bad_df)


def test_invalid_discount_range_raises_error():
    bad_df = pd.DataFrame([{
        "order_id": 1003,
        "product_id": 1,
        "date": "2024-05-01",
        "quantity": 1,
        "unit_price": 10.0,
        "discount": 1.25,  # 125% discount is invalid
    }])
    with pytest.raises(DataValidationError, match="Discounts must be between 0.0"):
        validate_raw_transactions(bad_df)


def test_duplicate_daily_product_records_raise_error():
    dup_df = pd.DataFrame([
        {
            "product_id": 5,
            "date": "2024-05-01",
            "total_units_sold": 10,
            "total_revenue": 100.0,
            "closing_stock": 50,
            "stockout_flag": 0,
        },
        {
            "product_id": 5,
            "date": "2024-05-01",  # Duplicate key
            "total_units_sold": 12,
            "total_revenue": 120.0,
            "closing_stock": 38,
            "stockout_flag": 0,
        },
    ])
    with pytest.raises(DataValidationError, match="duplicate"):
        validate_daily_aggregations(dup_df)