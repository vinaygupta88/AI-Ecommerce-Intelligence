from typing import List
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when incoming raw data violates business logic or schema bounds."""
    pass


def validate_raw_transactions(df: pd.DataFrame) -> bool:
    required_cols = {"order_id", "product_id", "date", "quantity", "unit_price", "discount"}
    missing = required_cols - set(df.columns)
    if missing:
        raise DataValidationError(f"Missing required columns in transactions: {missing}")

    if df["order_id"].isnull().any() or df["product_id"].isnull().any():
        raise DataValidationError("Found null values in order_id or product_id.")

    if (df["quantity"] <= 0).any():
        invalid_count = (df["quantity"] <= 0).sum()
        raise DataValidationError(f"Found {invalid_count} records with quantity <= 0.")

    if (df["unit_price"] < 0).any():
        raise DataValidationError("Found negative unit_price values.")

    if not df["discount"].between(0.0, 1.0).all():
        raise DataValidationError("Discounts must be between 0.0 (0%) and 1.0 (100%).")

    logger.info("Raw transaction validation passed: %d rows verified.", len(df))
    return True


def validate_daily_aggregations(df: pd.DataFrame) -> bool:
    required_cols = {
        "product_id",
        "date",
        "total_units_sold",
        "total_revenue",
        "closing_stock",
        "stockout_flag",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise DataValidationError(f"Missing required columns in daily sales: {missing}")

    duplicates = df.duplicated(subset=["product_id", "date"]).sum()
    if duplicates > 0:
        raise DataValidationError(f"Found {duplicates} duplicate (product_id, date) rows.")

    if (df["total_units_sold"] < 0).any():
        raise DataValidationError("Daily total_units_sold cannot be negative.")

    if (df["closing_stock"] < 0).any():
        raise DataValidationError("Daily closing_stock cannot be negative.")

    logger.info("Daily aggregation validation passed: %d records verified.", len(df))
    return True