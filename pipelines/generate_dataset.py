"""
pipelines/generate_dataset.py
Generates a realistic, deterministic retail dataset with inventory dynamics.
Zero-cost, fully reproducible via seed.
"""

import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import logging
from ml.features.validation import validate_raw_transactions, validate_daily_aggregations

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
RANDOM_SEED = 42
START_DATE = datetime(2023, 1, 1)
DAYS_COUNT = 730  # 2 full years (2023-2024)
NUM_PRODUCTS = 50

CATEGORIES = {
    "Electronics": {"base_demand": 18, "price_range": (45.0, 450.0), "lead_time": (5, 12)},
    "Apparel": {"base_demand": 35, "price_range": (15.0, 95.0), "lead_time": (7, 14)},
    "Home & Kitchen": {"base_demand": 22, "price_range": (20.0, 180.0), "lead_time": (4, 10)},
    "Beauty & Health": {"base_demand": 28, "price_range": (10.0, 75.0), "lead_time": (3, 7)},
    "Fitness & Outdoors": {"base_demand": 14, "price_range": (30.0, 220.0), "lead_time": (6, 15)},
}


def build_product_catalog(num_products: int = NUM_PRODUCTS) -> pd.DataFrame:
    """Generates the master product catalog."""
    np.random.seed(RANDOM_SEED)
    categories_list = list(CATEGORIES.keys())
    products = []

    for i in range(1, num_products + 1):
        cat_name = categories_list[i % len(categories_list)]
        cat_meta = CATEGORIES[cat_name]
        sku = f"SKU-{cat_name[:3].upper()}-{i:04d}"
        price = round(np.random.uniform(*cat_meta["price_range"]), 2)
        lead_time = int(np.random.randint(*cat_meta["lead_time"]))
        reorder_point = int(cat_meta["base_demand"] * lead_time * 1.2)
        target_stock = int(reorder_point * 2.5)

        products.append({
            "product_id": i,
            "sku": sku,
            "name": f"{cat_name} Item {i:03d}",
            "category": cat_name,
            "base_price": price,
            "lead_time_days": lead_time,
            "reorder_point": reorder_point,
            "target_stock": target_stock,
        })

    return pd.DataFrame(products)


def simulate_retail_demand_and_inventory(products_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Simulates transaction streams and daily inventory ledgers over 730 days.
    Accounts for:
      - Weekly seasonality (weekends have +40% demand)
      - Monthly trends & holidays (Q4 holiday surge)
      - Random promotions (20% discount causing demand spikes)
      - Stockouts: when stock == 0, sales = 0 regardless of demand
      - Supplier replenishment orders arriving after lead_time_days
    """
    np.random.seed(RANDOM_SEED)
    dates = [START_DATE + timedelta(days=d) for d in range(DAYS_COUNT)]

    raw_transactions = []
    daily_records = []
    order_id_seq = 100000

    logger.info("Simulating daily operations across %d products over %d days...", len(products_df), DAYS_COUNT)

    for _, prod in products_df.iterrows():
        p_id = int(prod["product_id"])
        cat = prod["category"]
        base_demand = CATEGORIES[cat]["base_demand"]
        price = float(prod["base_price"])
        lead_time = int(prod["lead_time_days"])
        reorder_point = int(prod["reorder_point"])
        target_stock = int(prod["target_stock"])

        current_stock = target_stock
        pending_orders = []  # List of tuples: (arrival_date, quantity)

        for current_date in dates:
            # 1. Process arriving supplier replenishments
            arrived_units = sum(qty for arr_date, qty in pending_orders if arr_date == current_date)
            current_stock += arrived_units
            pending_orders = [(arr_date, qty) for arr_date, qty in pending_orders if arr_date > current_date]

            # 2. Demand Drivers
            # Day of week effect (Saturday/Sunday peak)
            dow = current_date.weekday()
            dow_mult = 1.4 if dow in [5, 6] else 1.0

            # Q4 / Holiday surge (November - December)
            month = current_date.month
            season_mult = 1.5 if month in [11, 12] else (1.15 if month in [6, 7] else 0.95)

            # Random promotional event (~8% chance per day)
            is_promo = 1 if np.random.rand() < 0.08 else 0
            promo_discount = 0.20 if is_promo else 0.0
            promo_mult = 1.7 if is_promo else 1.0

            # Compute latent customer demand (Poisson distributed with random noise)
            lambda_demand = max(1.0, base_demand * dow_mult * season_mult * promo_mult)
            customer_demand = np.random.poisson(lam=lambda_demand)

            # 3. Realized Sales (Cannot exceed current inventory)
            if current_stock <= 0:
                realized_units = 0
                stockout_flag = 1
            else:
                stockout_flag = 0
                realized_units = min(current_stock, customer_demand)

            current_stock -= realized_units
            effective_unit_price = round(price * (1.0 - promo_discount), 2)
            total_revenue = round(realized_units * effective_unit_price, 2)

            # 4. Generate granular customer orders for this day if units sold > 0
            if realized_units > 0:
                units_remaining = realized_units
                while units_remaining > 0:
                    order_qty = min(units_remaining, np.random.choice([1, 2, 3, 4], p=[0.65, 0.20, 0.10, 0.05]))
                    units_remaining -= order_qty
                    raw_transactions.append({
                        "order_id": order_id_seq,
                        "product_id": p_id,
                        "date": current_date.strftime("%Y-%m-%d"),
                        "quantity": int(order_qty),
                        "unit_price": effective_unit_price,
                        "discount": promo_discount,
                    })
                    order_id_seq += 1

            # 5. Inventory Replenishment Logic
            # If inventory drops below reorder point and no order is already in transit
            if current_stock <= reorder_point and len(pending_orders) == 0:
                order_qty = target_stock - current_stock
                # Add lead time jitter (+/- 1 day) to reflect real supplier variance
                actual_lead_time = max(1, lead_time + np.random.choice([-1, 0, 1], p=[0.2, 0.6, 0.2]))
                arrival_date = current_date + timedelta(days=int(actual_lead_time))
                pending_orders.append((arrival_date, order_qty))

            # 6. Log Daily Summary Record
            daily_records.append({
                "product_id": p_id,
                "date": current_date.strftime("%Y-%m-%d"),
                "total_units_sold": int(realized_units),
                "unfulfilled_demand": int(max(0, customer_demand - realized_units)),
                "total_revenue": total_revenue,
                "closing_stock": int(current_stock),
                "promotional_flag": is_promo,
                "discount_pct": promo_discount,
                "stockout_flag": stockout_flag,
            })

    transactions_df = pd.DataFrame(raw_transactions)
    daily_df = pd.DataFrame(daily_records)
    return transactions_df, daily_df


def main():
    os.makedirs("ml/data/raw", exist_ok=True)
    os.makedirs("ml/data/processed", exist_ok=True)

    logger.info("Starting Phase 2 Dataset Pipeline...")

    # Step A: Build Master Product Catalog
    products_df = build_product_catalog(num_products=NUM_PRODUCTS)
    products_df.to_csv("ml/data/raw/product_catalog.csv", index=False)
    products_df.to_parquet("ml/data/processed/clean_product_catalog.parquet", index=False)
    logger.info("Product catalog saved (%d products).", len(products_df))

    # Step B: Simulate Operations
    raw_tx_df, daily_df = simulate_retail_demand_and_inventory(products_df)

    # Step C: Save Raw Transactions
    raw_tx_path = "ml/data/raw/raw_transactions.csv"
    raw_tx_df.to_csv(raw_tx_path, index=False)
    logger.info("Raw transactions saved: %s (%d rows)", raw_tx_path, len(raw_tx_df))

    # Step D: Run Strict Data Validations
    logger.info("Validating dataset integrity...")
    validate_raw_transactions(raw_tx_df)
    validate_daily_aggregations(daily_df)

    # Step E: Save Canonical Processed Dataset (Parquet format for speed & compression)
    processed_daily_path = "ml/data/processed/daily_sales_inventory.parquet"
    daily_df.to_parquet(processed_daily_path, index=False)
    logger.info("Clean processed daily dataset saved: %s (%d rows)", processed_daily_path, len(daily_df))

    print("\n---------------------------------------------------------")
    print("PHASE 2 SUMMARY STATS:")
    print(f"Total Products:         {len(products_df)}")
    print(f"Total Orders Generated: {len(raw_tx_df):,}")
    print(f"Total Daily Rows:       {len(daily_df):,} (50 SKUs x 730 Days)")
    print(f"Total Units Sold:       {daily_df['total_units_sold'].sum():,}")
    print(f"Total Revenue:          ${daily_df['total_revenue'].sum():,.2f}")
    print(f"Stockout Incidents:     {daily_df['stockout_flag'].sum():,} days")
    print("---------------------------------------------------------")


if __name__ == "__main__":
    main()