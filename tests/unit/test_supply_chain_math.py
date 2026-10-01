"""
tests/unit/test_supply_chain_math.py
Unit tests verifying replenishment math (Lead Time Demand, Safety Stock, ROP).
"""

from ml.inference.predictor import InferenceService


def test_reorder_math_triggers_when_stock_below_rop():
    service = InferenceService()

    # Inputs:
    # 7-day predicted demand = 140 units (Avg daily demand = 20 units/day)
    # Lead time = 5 days -> Lead Time Demand = 20 * 5 = 100 units
    # Current stock = 80 units
    # Target warehouse capacity = 300 units
    res = service.calculate_reorder_recommendation(
        predicted_7d_demand=140.0,
        current_stock=80,
        lead_time_days=5,
        daily_std_demand=4.0,
        target_stock=300,
        service_level_z=1.65,
    )

    assert res["lead_time_demand"] == 100.0
    assert res["safety_stock"] > 0
    assert res["reorder_point"] > res["lead_time_demand"]
    # Since current stock (80) is below ROP (> 100), reorder must trigger
    assert res["reorder_needed"] is True
    # Suggested quantity: Target (300) - Current (80) = 220 units
    assert res["suggested_reorder_qty"] == 220


def test_reorder_math_does_not_trigger_when_stock_is_healthy():
    service = InferenceService()

    res = service.calculate_reorder_recommendation(
        predicted_7d_demand=70.0,
        current_stock=250,  # High stock
        lead_time_days=3,
        daily_std_demand=2.0,
        target_stock=300,
        service_level_z=1.65,
    )

    assert res["reorder_needed"] is False
    assert res["suggested_reorder_qty"] == 0