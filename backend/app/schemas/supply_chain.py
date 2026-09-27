from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Health & Diagnostics ---
class HealthResponse(BaseModel):
    status: str
    database: str
    ml_models: str
    timestamp: datetime


# --- Category & Product Schemas ---
class CategoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None


class InventoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_stock: int
    safety_stock: int
    reorder_point: int
    updated_at: datetime


class ProductListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: str
    base_price: float
    current_stock: int
    reorder_point: int
    stock_status: str


class ProductDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: str
    base_price: float
    lead_time_days: int
    reorder_point: int
    target_stock: int
    current_stock: int
    safety_stock: int
    created_at: datetime


# --- ML Forecasting & Prediction Schemas ---
class ReorderAdvice(BaseModel):
    reorder_needed: bool
    suggested_reorder_qty: int
    safety_stock: int
    reorder_point: int
    lead_time_demand: float


class ForecastResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    current_stock: int
    predicted_demand_next_7d: float
    stockout_probability: float
    is_anomaly: bool
    reorder_advice: ReorderAdvice
    business_explanation: str
    model_version: str = "LightGBM-Champion-v1"


class DemandPredictRequest(BaseModel):
    product_id: int
    current_stock: int = Field(..., ge=0, description="Current warehouse stock")
    base_price: float = Field(..., gt=0.0, description="Item price")
    lead_time_days: int = Field(7, ge=1, le=60)
    sales_velocity_ratio: float = Field(1.0, ge=0.0)
    rolling_mean_7: float = Field(..., ge=0.0)
    rolling_std_7: float = Field(0.0, ge=0.0)
    promotional_flag: int = Field(0, ge=0, le=1)


# --- Alerts Schemas ---
class AlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    sku: str
    product_name: str
    alert_type: str
    severity: str
    message: str
    is_resolved: bool
    created_at: datetime


# --- Dashboard Summary Schemas ---
class DashboardSummary(BaseModel):
    total_skus: int
    total_inventory_units: int
    critical_stockout_skus: int
    active_alerts_count: int
    fleet_7d_forecasted_demand: float
    top_risk_products: List[ProductListItem]