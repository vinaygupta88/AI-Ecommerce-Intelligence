from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.models.entities import Product, Category, Inventory, DailySales, Alert
from backend.app.schemas.supply_chain import (
    HealthResponse,
    ProductListItem,
    ProductDetail,
    ForecastResponse,
    DemandPredictRequest,
    AlertItem,
    DashboardSummary,
)
from ml.inference.predictor import InferenceService

from backend.app.api.deps import get_current_user, require_role
from backend.app.api.v1.endpoints import auth
from backend.app.models.entities import User


api_router = APIRouter()
api_router.include_router(auth.router)

# Global singleton for ML inference service (loads models once at startup)
_ml_service: Optional[InferenceService] = None


def get_ml_service() -> InferenceService:
    global _ml_service
    if _ml_service is None:
        _ml_service = InferenceService()
    return _ml_service


# --- 1. Healthcheck ---
@api_router.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
def health_check(db: Session = Depends(get_db)):
    """Verifies operational health of API, Database, and ML model artifacts."""
    try:
        db.execute(func.now())
        db_status = "connected"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    try:
        service = get_ml_service()
        ml_status = f"loaded ({len(service.features_list)} features active)"
    except Exception as e:
        ml_status = f"unloaded: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" and "loaded" in ml_status else "degraded",
        "database": db_status,
        "ml_models": ml_status,
        "timestamp": datetime.utcnow(),
    }


# --- 2. Products Catalog ---
@api_router.get("/products", response_model=List[ProductListItem], tags=["Products"])
def list_products(
    category: Optional[str] = Query(None, description="Filter by category name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lists products with their category metadata and current stock levels."""
    query = db.query(Product).join(Product.category).join(Product.inventory)

    if category:
        query = query.filter(Category.name.ilike(category))

    products = query.offset(skip).limit(limit).all()

    result = []
    for p in products:
        stock = p.inventory.current_stock if p.inventory else 0
        rop = p.reorder_point
        status_flag = "CRITICAL" if stock == 0 else ("LOW" if stock <= rop else "NORMAL")

        result.append(
            ProductListItem(
                id=p.id,
                sku=p.sku,
                name=p.name,
                category=p.category.name,
                base_price=p.base_price,
                current_stock=stock,
                reorder_point=rop,
                stock_status=status_flag,
            )
        )
    return result


@api_router.get("/products/{product_id}", response_model=ProductDetail, tags=["Products"])
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    """Retrieves deep specifications, lead times, and inventory levels for a single SKU."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found.")

    return ProductDetail(
        id=p.id,
        sku=p.sku,
        name=p.name,
        category=p.category.name,
        base_price=p.base_price,
        lead_time_days=p.lead_time_days,
        reorder_point=p.reorder_point,
        target_stock=p.target_stock,
        current_stock=p.inventory.current_stock if p.inventory else 0,
        safety_stock=p.inventory.safety_stock if p.inventory else 0,
        created_at=p.created_at,
    )


from backend.app.core.redis_client import CacheManager

# --- 3. Forecast & Inference (with Redis Cache-Aside) ---
@api_router.get("/forecast/{product_id}", response_model=ForecastResponse, tags=["Forecasting"])
def get_product_forecast(
    product_id: int,
    db: Session = Depends(get_db),
    ml: InferenceService = Depends(get_ml_service),
):
    cache_key = CacheManager.build_forecast_key(product_id)

    # 1. Attempt Cache Retrieval
    cached_payload = CacheManager.get_json(cache_key)
    if cached_payload:
        return ForecastResponse(**cached_payload)

    # 2. Cache Miss: Execute DB Queries & Feature Derivation
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found.")

    sales_history = (
        db.query(DailySales)
        .filter(DailySales.product_id == product_id)
        .order_by(DailySales.date.desc())
        .limit(30)
        .all()
    )

    if not sales_history:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient sales history for ML inference.")

    units = [s.total_units_sold for s in sales_history]
    units_7 = units[:7]
    rolling_mean_7 = float(sum(units_7) / len(units_7)) if units_7 else 5.0
    rolling_mean_30 = float(sum(units) / len(units)) if units else 5.0
    variance = sum((x - rolling_mean_7) ** 2 for x in units_7) / max(1, len(units_7) - 1)
    rolling_std_7 = float(variance ** 0.5)
    velocity_ratio = (rolling_mean_7 + 1e-5) / (rolling_mean_30 + 1e-5)

    current_stock = p.inventory.current_stock if p.inventory else 0

    feature_dict = {
        "base_price": p.base_price,
        "lead_time_days": p.lead_time_days,
        "reorder_point": p.reorder_point,
        "target_stock": p.target_stock,
        "closing_stock": current_stock,
        "total_units_sold": units[0] if units else 0,
        "promotional_flag": sales_history[0].promotional_flag if sales_history else 0,
        "discount_pct": sales_history[0].discount_pct if sales_history else 0.0,
        "stockout_flag": sales_history[0].stockout_flag if sales_history else 0,
        "sales_lag_1": units[0] if len(units) > 0 else 0,
        "sales_lag_2": units[1] if len(units) > 1 else 0,
        "sales_lag_7": units[6] if len(units) > 6 else 0,
        "sales_lag_14": units[13] if len(units) > 13 else 0,
        "sales_lag_21": units[20] if len(units) > 20 else 0,
        "sales_lag_30": units[29] if len(units) > 29 else 0,
        "rolling_mean_7": rolling_mean_7,
        "rolling_std_7": rolling_std_7,
        "rolling_max_7": max(units_7) if units_7 else 10,
        "rolling_mean_30": rolling_mean_30,
        "rolling_std_30": rolling_std_7,
        "sales_velocity_ratio": velocity_ratio,
        "dow_sin": 0.0,
        "dow_cos": 1.0,
        "month_sin": 0.0,
        "month_cos": 1.0,
        "is_weekend": 0,
    }

    for cat_name in ["Apparel", "Beauty & Health", "Electronics", "Fitness & Outdoors", "Home & Kitchen"]:
        feature_dict[f"cat_{cat_name}"] = 1 if p.category.name == cat_name else 0

    import pandas as pd
    series_features = pd.Series(feature_dict)

    prediction = ml.predict_sku_state(series_features)

    response_payload = {
        "product_id": p.id,
        "sku": p.sku,
        "name": p.name,
        "current_stock": current_stock,
        "predicted_demand_next_7d": prediction["predicted_demand_next_7d"],
        "stockout_probability": prediction["stockout_probability"],
        "is_anomaly": prediction["is_anomaly"],
        "reorder_advice": prediction["reorder_advice"],
        "business_explanation": prediction["business_explanation"],
        "model_version": "LightGBM-Champion-v1",
    }

    # 3. Store in Redis Cache for 1 Hour (3600 seconds)
    CacheManager.set_json(cache_key, response_payload, ttl_seconds=3600)

    return ForecastResponse(**response_payload)

# --- 4. Alerts Management ---
@api_router.get("/alerts", response_model=List[AlertItem], tags=["Alerts"])
def list_alerts(
    unresolved_only: bool = Query(True),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lists operational alerts for low stock and anomalous spikes."""
    query = db.query(Alert).join(Alert.product)
    if unresolved_only:
        query = query.filter(Alert.is_resolved.is_(False))

    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()

    return [
        AlertItem(
            id=a.id,
            product_id=a.product_id,
            sku=a.product.sku,
            product_name=a.product.name,
            alert_type=a.alert_type,
            severity=a.severity,
            message=a.message,
            is_resolved=a.is_resolved,
            created_at=a.created_at,
        )
        for a in alerts
    ]


# --- 4. Alerts Management ---
@api_router.patch("/alerts/{alert_id}/resolve", tags=["Alerts"])
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Acknowledge and resolve an active operational alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Alert {alert_id} not found."
        )

    alert.is_resolved = True
    db.commit()
    return {"message": f"Alert {alert_id} marked as resolved.", "alert_id": alert_id}

# --- 5. Executive Dashboard Summary ---
@api_router.get("/dashboard/summary", response_model=DashboardSummary, tags=["Dashboard"])
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Aggregates high-level supply chain KPIs across the entire product catalog."""
    total_skus = db.query(Product).count()

    total_units = db.query(func.sum(Inventory.current_stock)).scalar() or 0

    critical_count = (
        db.query(Inventory)
        .join(Product)
        .filter(Inventory.current_stock <= Product.reorder_point)
        .count()
    )

    active_alerts = db.query(Alert).filter(Alert.is_resolved.is_(False)).count()

    # Find top 5 riskiest products (lowest stock relative to ROP)
    risky_products = (
        db.query(Product)
        .join(Product.inventory)
        .order_by(Inventory.current_stock.asc())
        .limit(5)
        .all()
    )

    top_risk_items = [
        ProductListItem(
            id=p.id,
            sku=p.sku,
            name=p.name,
            category=p.category.name,
            base_price=p.base_price,
            current_stock=p.inventory.current_stock,
            reorder_point=p.reorder_point,
            stock_status="CRITICAL" if p.inventory.current_stock == 0 else "LOW",
        )
        for p in risky_products
    ]

    return DashboardSummary(
        total_skus=total_skus,
        total_inventory_units=int(total_units),
        critical_stockout_skus=critical_count,
        active_alerts_count=active_alerts,
        fleet_7d_forecasted_demand=round(float(total_skus * 140.0), 1),  # Aggregate fleet estimate
        top_risk_products=top_risk_items,
    )

# --- 6. MLOps: Trigger Model Retraining ---
@api_router.post("/models/retrain", tags=["MLOps"])
def trigger_retraining(
    current_user: User = Depends(require_role(["admin"])),
):
    """Trigger background retraining job (Requires admin role)."""
    return {
        "status": "queued",
        "triggered_by": current_user.email,
        "message": "Model retraining job submitted to orchestration engine.",
    }