import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class InferenceService:
    def __init__(self, models_dir: str = os.path.join("ml", "models")):
        self.models_dir = models_dir
        self.forecaster = None
        self.classifier = None
        self.anomaly_detector = None
        self.features_list: List[str] = []
        self._load_artifacts()

    def _load_artifacts(self):
        """Loads serialized models and metadata."""
        meta_path = os.path.join(self.models_dir, "forecasting_metadata.json")
        forecaster_path = os.path.join(self.models_dir, "demand_forecaster.joblib")
        classifier_path = os.path.join(self.models_dir, "stockout_classifier.joblib")
        anomaly_path = os.path.join(self.models_dir, "anomaly_detector.joblib")

        if not os.path.exists(forecaster_path):
            raise FileNotFoundError(f"Model artifacts not found in {self.models_dir}. Run Phase 5 first.")

        with open(meta_path, "r", encoding="utf-8") as f:
            self.features_list = json.load(f)["feature_names"]

        self.forecaster = joblib.load(forecaster_path)
        self.classifier = joblib.load(classifier_path)
        self.anomaly_detector = joblib.load(anomaly_path)
        logger.info("InferenceService: All 3 models loaded successfully.")

    def calculate_reorder_recommendation(
        self,
        predicted_7d_demand: float,
        current_stock: int,
        lead_time_days: int,
        daily_std_demand: float,
        target_stock: int,
        service_level_z: float = 1.65,  # 95% service level
    ) -> Dict[str, Any]:
        avg_daily_demand = max(0.1, predicted_7d_demand / 7.0)
        lead_time_demand = avg_daily_demand * lead_time_days

        # Safety Stock = Z * std_dev * sqrt(lead_time)
        safety_stock = int(np.ceil(service_level_z * max(1.0, daily_std_demand) * np.sqrt(lead_time_days)))
        reorder_point = int(np.ceil(lead_time_demand + safety_stock))

        # Reorder trigger
        reorder_needed = current_stock <= reorder_point
        suggested_qty = max(0, target_stock - current_stock) if reorder_needed else 0

        return {
            "reorder_needed": bool(reorder_needed),
            "suggested_reorder_qty": int(suggested_qty),
            "safety_stock": int(safety_stock),
            "reorder_point": int(reorder_point),
            "lead_time_demand": round(float(lead_time_demand), 2),
        }

    def generate_explanation(
        self,
        features: pd.Series,
        forecast_7d: float,
        stockout_prob: float,
        is_anomaly: bool,
    ) -> str:
        notes = []

        velocity = features.get("sales_velocity_ratio", 1.0)
        if velocity > 1.25:
            notes.append(f"Demand is accelerating rapidly ({velocity:.1f}x 30-day baseline).")
        elif velocity < 0.75:
            notes.append(f"Demand has slowed below average ({velocity:.1f}x 30-day baseline).")

        if features.get("promotional_flag", 0) == 1:
            notes.append("Active 20% discount is driving elevated forecast volume.")

        if stockout_prob >= 0.70:
            notes.append(f"CRITICAL RISK: {stockout_prob * 100:.0f}% chance of running out before next replenishment.")
        elif stockout_prob >= 0.35:
            notes.append("ELEVATED RISK: Current stock is near the reorder point.")

        if is_anomaly:
            notes.append("FLAGGED ANOMALY: Today's sales behavior deviates significantly from historical patterns.")

        if not notes:
            notes.append("Demand and inventory trajectories are operating within normal baseline bounds.")

        return " ".join(notes)

    def predict_sku_state(self, feature_row: pd.Series) -> Dict[str, Any]:
        # Ensure DataFrame has exact expected columns in order
        feature_vector = pd.DataFrame([feature_row.reindex(self.features_list, fill_value=0).to_dict()])

        # 1. Demand Forecast
        pred_demand = float(np.maximum(0, self.forecaster.predict(feature_vector)[0]))

        # 2. Stockout Probability
        prob_stockout = float(self.classifier.predict_proba(feature_vector)[0][1])

        # 3. Anomaly Detection
        anomaly_features = pd.DataFrame([{
            "total_units_sold": feature_row.get("total_units_sold", 0),
            "sales_velocity_ratio": feature_row.get("sales_velocity_ratio", 1.0),
            "rolling_std_7": feature_row.get("rolling_std_7", 0.0),
            "base_price": feature_row.get("base_price", 10.0),
            "discount_pct": feature_row.get("discount_pct", 0.0),
        }])
        anomaly_flag = bool(self.anomaly_detector.predict(anomaly_features)[0] == -1)

        # 4. Inventory Advice
        reorder_info = self.calculate_reorder_recommendation(
            predicted_7d_demand=pred_demand,
            current_stock=int(feature_row.get("closing_stock", 0)),
            lead_time_days=int(feature_row.get("lead_time_days", 7)),
            daily_std_demand=float(feature_row.get("rolling_std_7", 3.0)),
            target_stock=int(feature_row.get("target_stock", 100)),
        )

        # 5. Business Explanation
        explanation = self.generate_explanation(feature_row, pred_demand, prob_stockout, anomaly_flag)

        return {
            "predicted_demand_next_7d": round(pred_demand, 1),
            "stockout_probability": round(prob_stockout, 4),
            "is_anomaly": anomaly_flag,
            "reorder_advice": reorder_info,
            "business_explanation": explanation,
        }