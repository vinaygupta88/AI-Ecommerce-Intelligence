import os
import pandas as pd
from datetime import datetime
from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models.entities import Category, Product, Inventory, DailySales, Alert, User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
PROCESSED_DIR = os.path.join("ml", "data", "processed")


def seed_database():
    db = SessionLocal()
    try:
        print("[*] Checking existing database records...")
        if db.query(Product).count() > 0:
            print("[WARN] Database already contains records. Skipping seed.")
            return

        print("[*] Creating default administrative & user accounts...")
        admin_user = User(
            email="admin@ecommerce.ai",
            hashed_password=pwd_context.hash("AdminPass123!"),
            full_name="System Administrator",
            role="admin",
        )
        ds_user = User(
            email="scientist@ecommerce.ai",
            hashed_password=pwd_context.hash("ScientistPass123!"),
            full_name="Lead Data Scientist",
            role="data_scientist",
        )
        biz_user = User(
            email="manager@ecommerce.ai",
            hashed_password=pwd_context.hash("ManagerPass123!"),
            full_name="Inventory Manager",
            role="business_user",
        )
        db.add_all([admin_user, ds_user, biz_user])
        db.commit()

        print("[*] Loading catalog parquet...")
        prod_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "clean_product_catalog.parquet"))

        # 1. Seed Categories
        categories = prod_df["category"].unique()
        cat_map = {}
        for cat_name in categories:
            cat_obj = Category(name=cat_name, description=f"Products belonging to {cat_name}")
            db.add(cat_obj)
            db.flush()
            cat_map[cat_name] = cat_obj.id

        # 2. Seed Products
        print(f"[*] Seeding {len(prod_df)} products...")
        product_map = {}
        for _, row in prod_df.iterrows():
            prod_obj = Product(
                id=int(row["product_id"]),
                category_id=cat_map[row["category"]],
                sku=str(row["sku"]),
                name=str(row["name"]),
                base_price=float(row["base_price"]),
                lead_time_days=int(row["lead_time_days"]),
                reorder_point=int(row["reorder_point"]),
                target_stock=int(row["target_stock"]),
            )
            db.add(prod_obj)
            product_map[prod_obj.id] = prod_obj

        db.commit()

        # 3. Seed Daily Sales and Inventory
        print("[*] Loading daily sales & inventory parquet...")
        daily_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "daily_sales_inventory.parquet"))
        daily_df["date"] = pd.to_datetime(daily_df["date"]).dt.date

        print(f"[*] Seeding {len(daily_df):,} daily sales rows (in batch)...")
        # Use bulk insert for high performance
        sales_records = []
        for _, row in daily_df.iterrows():
            sales_records.append(
                DailySales(
                    product_id=int(row["product_id"]),
                    date=row["date"],
                    total_units_sold=int(row["total_units_sold"]),
                    total_revenue=float(row["total_revenue"]),
                    unfulfilled_demand=int(row["unfulfilled_demand"]),
                    closing_stock=int(row["closing_stock"]),
                    promotional_flag=int(row["promotional_flag"]),
                    discount_pct=float(row["discount_pct"]),
                    stockout_flag=int(row["stockout_flag"]),
                )
            )

        db.bulk_save_objects(sales_records)
        db.commit()

        # 4. Seed Current Inventory Snapshot (latest closing stock per product)
        print("[*] Initializing active inventory states...")
        latest_date = daily_df["date"].max()
        latest_snapshot = daily_df[daily_df["date"] == latest_date]

        for _, row in latest_snapshot.iterrows():
            p_id = int(row["product_id"])
            prod_meta = prod_df[prod_df["product_id"] == p_id].iloc[0]
            current_stock = int(row["closing_stock"])
            reorder_pt = int(prod_meta["reorder_point"])
            safety_stk = int(reorder_pt * 0.4)

            inv_obj = Inventory(
                product_id=p_id,
                current_stock=current_stock,
                safety_stock=safety_stk,
                reorder_point=reorder_pt,
            )
            db.add(inv_obj)

            # Generate initial operational alert if stock is critical
            if current_stock <= reorder_pt:
                severity = "CRITICAL" if current_stock == 0 else "HIGH"
                db.add(
                    Alert(
                        product_id=p_id,
                        alert_type="STOCKOUT",
                        severity=severity,
                        message=f"Product {prod_meta['sku']} ({prod_meta['name']}) has stock {current_stock}, below ROP {reorder_pt}.",
                    )
                )

        db.commit()
        print("[SUCCESS] Database seeding complete!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database seeding failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()