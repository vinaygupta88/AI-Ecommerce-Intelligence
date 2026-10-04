import os
import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.join("ml", "data", "processed")


def load_raw_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    daily_path = os.path.join(PROCESSED_DIR, "daily_sales_inventory.parquet")
    prod_path = os.path.join(PROCESSED_DIR, "clean_product_catalog.parquet")

    if not os.path.exists(daily_path) or not os.path.exists(prod_path):
        raise FileNotFoundError("Clean data missing. Run pipelines/generate_dataset.py first.")

    daily_df = pd.read_parquet(daily_path)
    prod_df = pd.read_parquet(prod_path)
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df = daily_df.sort_values(["product_id", "date"]).reset_index(drop=True)
    return daily_df, prod_df


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    dow = df["date"].dt.dayofweek
    month = df["date"].dt.month

    # Cyclical day of week (0 to 6)
    df["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    df["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)

    # Cyclical month of year (1 to 12)
    df["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12.0)

    df["is_weekend"] = dow.isin([5, 6]).astype(int)
    return df


def add_lag_and_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    grouped = df.groupby("product_id")["total_units_sold"]

    # 1. Historical Lag Features (units sold at t-k)
    for lag in [1, 2, 7, 14, 21, 30]:
        df[f"sales_lag_{lag}"] = grouped.shift(lag)

    # 2. Rolling Window Statistics (trailing windows shifted by 1 day)
    # shift(1) guarantees that today's sales are NOT included in today's features
    shifted = grouped.shift(1)
    df["rolling_mean_7"] = shifted.groupby(df["product_id"]).transform(lambda s: s.rolling(7, min_periods=3).mean())
    df["rolling_std_7"] = shifted.groupby(df["product_id"]).transform(lambda s: s.rolling(7, min_periods=3).std()).fillna(0)
    df["rolling_max_7"] = shifted.groupby(df["product_id"]).transform(lambda s: s.rolling(7, min_periods=3).max())

    df["rolling_mean_30"] = shifted.groupby(df["product_id"]).transform(lambda s: s.rolling(30, min_periods=7).mean())
    df["rolling_std_30"] = shifted.groupby(df["product_id"]).transform(lambda s: s.rolling(30, min_periods=7).std()).fillna(0)

    # Ratio of short-term velocity (7d) to long-term velocity (30d)
    # Identifies acceleration or deceleration in sales
    df["sales_velocity_ratio"] = (df["rolling_mean_7"] + 1e-5) / (df["rolling_mean_30"] + 1e-5)

    return df


def add_target_variables(df: pd.DataFrame, prod_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    prod_lead_times = dict(zip(prod_df["product_id"], prod_df["lead_time_days"]))
    df["lead_time_days"] = df["product_id"].map(prod_lead_times)

    # Target 1: Sum of sales over next 7 days (t+1 through t+7)
    # Calculated by rolling forward using negative indexing / shift
    indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=7)
    df["target_demand_next_7d"] = (
        df.groupby("product_id")["total_units_sold"]
        .transform(lambda s: s.shift(-1).rolling(window=indexer, min_periods=7).sum())
    )

    # Target 2: Stock-out classification within lead-time window
    # If the minimum closing stock in the next lead_time days is 0, stock-out occurs
    df["target_stockout_leadtime"] = 0
    grouped_stock = df.groupby("product_id")["closing_stock"]

    # Iterate over unique lead times to calculate forward min window
    for lt in prod_df["lead_time_days"].unique():
        p_ids = prod_df[prod_df["lead_time_days"] == lt]["product_id"].values
        fwd_indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=int(lt))
        
        subset_mask = df["product_id"].isin(p_ids)
        min_fwd_stock = (
            df[subset_mask].groupby("product_id")["closing_stock"]
            .transform(lambda s: s.shift(-1).rolling(window=fwd_indexer, min_periods=int(lt)).min())
        )
        df.loc[subset_mask, "target_stockout_leadtime"] = (min_fwd_stock == 0).astype(int)

    return df


def split_chronologically(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_end = pd.Timestamp("2024-06-30")
    val_end = pd.Timestamp("2024-09-30")

    train_df = df[df["date"] <= train_end].copy()
    val_df = df[(df["date"] > train_end) & (df["date"] <= val_end)].copy()
    test_df = df[df["date"] > val_end].copy()

    return train_df, val_df, test_df


def main():
    logger.info("Starting Phase 4 Feature Engineering Pipeline...")
    daily_df, prod_df = load_raw_data()

    # Step 1: Merge catalog attributes
    merged = daily_df.merge(
        prod_df[["product_id", "category", "base_price", "reorder_point", "target_stock"]],
        on="product_id",
        how="left",
    )

    # Step 2: One-hot encode category
    merged = pd.get_dummies(merged, columns=["category"], prefix="cat", drop_first=False)

    # Step 3: Calendar Features
    logger.info("Computing calendar and cyclical features...")
    df_features = add_calendar_features(merged)

    # Step 4: Lag & Rolling Features
    logger.info("Computing lag structures and rolling statistics...")
    df_features = add_lag_and_rolling_features(df_features)

    # Step 5: Targets
    logger.info("Formulating future targets (7-day demand & stock-out flag)...")
    df_features = add_target_variables(df_features, prod_df)

    # Step 6: Drop warm-up rows (first 30 days have NaN lag_30) and tail rows (last 7 days have NaN targets)
    logger.info("Cleaning warm-up buffer and tail horizon rows...")
    initial_rows = len(df_features)
    clean_df = df_features.dropna(subset=[
        "sales_lag_30",
        "rolling_mean_30",
        "target_demand_next_7d",
    ]).reset_index(drop=True)
    logger.info("Filtered %d boundary rows. Usable records: %d", initial_rows - len(clean_df), len(clean_df))

    # Step 7: Chronological Train / Val / Test Split
    logger.info("Splitting dataset chronologically...")
    train_df, val_df, test_df = split_chronologically(clean_df)

    # Save to Parquet
    train_path = os.path.join(PROCESSED_DIR, "features_train.parquet")
    val_path = os.path.join(PROCESSED_DIR, "features_val.parquet")
    test_path = os.path.join(PROCESSED_DIR, "features_test.parquet")

    train_df.to_parquet(train_path, index=False)
    val_df.to_parquet(val_path, index=False)
    test_df.to_parquet(test_path, index=False)

    print("\n---------------------------------------------------------")
    print("PHASE 4 FEATURE ENGINEERING SUMMARY:")
    print(f"Total Features Generated: {len(clean_df.columns)}")
    print(f"Train Records:  {len(train_df):,}  ({train_df['date'].min().date()} to {train_df['date'].max().date()})")
    print(f"Val Records:    {len(val_df):,}    ({val_df['date'].min().date()} to {val_df['date'].max().date()})")
    print(f"Test Records:   {len(test_df):,}   ({test_df['date'].min().date()} to {test_df['date'].max().date()})")
    print(f"Stockout Rate in Train: {train_df['target_stockout_leadtime'].mean() * 100:.2f}%")
    print("Files successfully generated in ml/data/processed/")
    print("---------------------------------------------------------")


if __name__ == "__main__":
    main()