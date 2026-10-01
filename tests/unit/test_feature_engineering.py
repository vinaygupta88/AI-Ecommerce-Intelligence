"""
tests/unit/test_feature_engineering.py
Unit tests verifying cyclical date transforms and zero-leakage rolling calculations.
"""

import numpy as np
import pandas as pd
from ml.features.build_features import add_calendar_features, add_lag_and_rolling_features


def test_cyclical_calendar_encoding_bounds():
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    df = pd.DataFrame({"date": dates})
    df = add_calendar_features(df)

    # Sine and cosine must strictly oscillate within [-1.0, 1.0]
    assert df["dow_sin"].between(-1.0, 1.0).all()
    assert df["dow_cos"].between(-1.0, 1.0).all()
    assert df["month_sin"].between(-1.0, 1.0).all()
    assert df["month_cos"].between(-1.0, 1.0).all()

    # Fundamental trigonometric identity: sin^2 + cos^2 = 1.0
    dow_identity = np.square(df["dow_sin"]) + np.square(df["dow_cos"])
    np.testing.assert_allclose(dow_identity, 1.0, atol=1e-5)


def test_zero_leakage_in_lag_and_rolling():
    """
    Asserts that today's feature row does NOT contain today's target sales.
    If sales spike today (e.g. 500 units), sales_lag_1 must still reflect yesterday.
    """
    data = [
        {"product_id": 1, "total_units_sold": 10},
        {"product_id": 1, "total_units_sold": 12},
        {"product_id": 1, "total_units_sold": 15},
        {"product_id": 1, "total_units_sold": 500},  # Sudden surge at index 3
    ]
    df = pd.DataFrame(data)
    df_feat = add_lag_and_rolling_features(df)

    # Row 3 (the 500 unit day)
    # lag_1 should equal row 2's sales (15), NOT 500
    assert df_feat.loc[3, "sales_lag_1"] == 15

    # rolling_mean_7 on row 3 must ONLY average rows 0, 1, and 2: (10 + 12 + 15) / 3 = 12.33
    expected_mean = (10 + 12 + 15) / 3.0
    assert np.isclose(df_feat.loc[3, "rolling_mean_7"], expected_mean, atol=1e-2)