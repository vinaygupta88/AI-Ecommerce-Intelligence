from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="business_user", nullable=False)  # admin, data_scientist, business_user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    base_price = Column(Float, nullable=False)
    lead_time_days = Column(Integer, default=7, nullable=False)
    reorder_point = Column(Integer, nullable=False)
    target_stock = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", uselist=False)
    daily_sales = relationship("DailySales", back_populates="product")
    predictions = relationship("Prediction", back_populates="product")
    alerts = relationship("Alert", back_populates="product")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    current_stock = Column(Integer, nullable=False, default=0)
    safety_stock = Column(Integer, nullable=False, default=0)
    reorder_point = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="inventory")


class DailySales(Base):
    __tablename__ = "daily_sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    total_units_sold = Column(Integer, nullable=False, default=0)
    total_revenue = Column(Float, nullable=False, default=0.0)
    unfulfilled_demand = Column(Integer, nullable=False, default=0)
    closing_stock = Column(Integer, nullable=False, default=0)
    promotional_flag = Column(Integer, nullable=False, default=0)
    discount_pct = Column(Float, nullable=False, default=0.0)
    stockout_flag = Column(Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="daily_sales")

    __table_args__ = (
        Index("idx_product_date", "product_id", "date", unique=True),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    prediction_date = Column(Date, nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False, default=7)
    forecasted_demand = Column(Float, nullable=False)
    stockout_probability = Column(Float, nullable=False)
    suggested_reorder_qty = Column(Integer, nullable=False, default=0)
    model_version = Column(String(50), nullable=False, default="LightGBM-v1")
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="predictions")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # STOCKOUT, ANOMALY, SURGE
    severity = Column(String(20), nullable=False)    # LOW, MEDIUM, HIGH, CRITICAL
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="alerts")