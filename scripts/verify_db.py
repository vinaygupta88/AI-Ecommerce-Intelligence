from backend.app.core.database import SessionLocal
from backend.app.models.entities import User, Category, Product, Inventory, DailySales, Alert


def verify_database():
    db = SessionLocal()
    try:
        print("[*] Connecting to PostgreSQL database...")
        user_count = db.query(User).count()
        cat_count = db.query(Category).count()
        prod_count = db.query(Product).count()
        inv_count = db.query(Inventory).count()
        sales_count = db.query(DailySales).count()
        alert_count = db.query(Alert).count()

        print("\n--- DATABASE VERIFICATION METRICS ---")
        print(f"Users:        {user_count} (Expected: 3)")
        print(f"Categories:   {cat_count} (Expected: 5)")
        print(f"Products:     {prod_count} (Expected: 50)")
        print(f"Inventory:    {inv_count} (Expected: 50)")
        print(f"Daily Sales:  {sales_count:,} (Expected: 36,500)")
        print(f"Active Alerts:{alert_count}")
        print("-------------------------------------")

        # Relational Join Verification
        first_prod = db.query(Product).first()
        print(f"\n[*] Testing Relational Join for SKU: {first_prod.sku}")
        print(f"    Product Name:   {first_prod.name}")
        print(f"    Category Name:  {first_prod.category.name}")
        print(f"    Current Stock:  {first_prod.inventory.current_stock}")
        print(f"    Lead Time Days: {first_prod.lead_time_days}")

        assert user_count == 3
        assert cat_count == 5
        assert prod_count == 50
        assert sales_count == 36500
        print("\n[SUCCESS] Relational database is healthy and ready for API backend.")

    finally:
        db.close()


if __name__ == "__main__":
    verify_database()