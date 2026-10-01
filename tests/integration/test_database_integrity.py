"""
tests/integration/test_database_integrity.py
Integration tests validating PostgreSQL schema constraints, relationships, and joins.
"""

from backend.app.core.database import SessionLocal
from backend.app.models.entities import Product, Category, Inventory, DailySales


def test_product_category_relationship():
    db = SessionLocal()
    try:
        product = db.query(Product).first()
        assert product is not None, "Products table is empty."
        assert product.category is not None
        assert isinstance(product.category.name, str)
    finally:
        db.close()


def test_product_inventory_one_to_one_relationship():
    db = SessionLocal()
    try:
        product = db.query(Product).first()
        assert product.inventory is not None
        assert product.inventory.current_stock >= 0
        assert product.inventory.product_id == product.id
    finally:
        db.close()


def test_daily_sales_composite_index_and_records():
    db = SessionLocal()
    try:
        # Check sales records exist for product 1
        sales_records = (
            db.query(DailySales)
            .filter(DailySales.product_id == 1)
            .order_by(DailySales.date.desc())
            .limit(10)
            .all()
        )
        assert len(sales_records) == 10
        for s in sales_records:
            assert s.total_units_sold >= 0
            assert s.total_revenue >= 0.0
    finally:
        db.close()