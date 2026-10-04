import os
import logging

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

PLOTS_DIR = os.path.join("docs", "plots")
REPORT_PATH = os.path.join("docs", "eda_report.md")


def load_datasets():
    daily_path = os.path.join(
        "ml",
        "data",
        "processed",
        "daily_sales_inventory.parquet"
    )

    prod_path = os.path.join(
        "ml",
        "data",
        "processed",
        "clean_product_catalog.parquet"
    )

    if not os.path.exists(daily_path) or not os.path.exists(prod_path):
        raise FileNotFoundError(
            "Processed dataset missing. "
            "Run 'python pipelines/generate_dataset.py' first."
        )

    logger.info("Loading processed datasets...")

    daily_df = pd.read_parquet(daily_path)
    prod_df = pd.read_parquet(prod_path)

    # Ensure date column is datetime
    daily_df["date"] = pd.to_datetime(daily_df["date"])

    # Merge daily sales/inventory data with product catalog
    merged_df = daily_df.merge(
        prod_df,
        on="product_id",
        how="left"
    )

    logger.info(
        "Loaded %s daily records and %s products.",
        f"{len(merged_df):,}",
        f"{len(prod_df):,}"
    )

    return merged_df, prod_df

def plot_sales_trend(df: pd.DataFrame):
    daily_agg = (
        df.groupby("date")["total_units_sold"]
        .sum()
        .reset_index()
    )

    # Calculate 30-day rolling average
    daily_agg["rolling_30"] = (
        daily_agg["total_units_sold"]
        .rolling(
            window=30,
            min_periods=7
        )
        .mean()
    )

    plt.figure(figsize=(14, 5))

    plt.plot(
        daily_agg["date"],
        daily_agg["total_units_sold"],
        color="#2563eb",
        linewidth=1.2,
        label="Daily Units Sold"
    )

    plt.plot(
        daily_agg["date"],
        daily_agg["rolling_30"],
        color="#dc2626",
        linewidth=2.0,
        label="30-Day Moving Average"
    )

    plt.title(
        "Total Units Sold Across All SKUs",
        fontsize=14,
        fontweight="bold"
    )

    plt.xlabel("Date", fontsize=11)
    plt.ylabel("Total Units", fontsize=11)

    plt.grid(
        True,
        linestyle="--",
        alpha=0.5
    )

    plt.legend()
    plt.tight_layout()

    out_file = os.path.join(
        PLOTS_DIR,
        "sales_trend.png"
    )

    plt.savefig(
        out_file,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    logger.info("Saved: %s", out_file)

def plot_category_distributions(df: pd.DataFrame):
    cat_agg = (
        df.groupby("category")
        .agg(
            total_units_sold=("total_units_sold", "sum"),
            total_revenue=("total_revenue", "sum")
        )
        .reset_index()
    )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14, 5)
    )

    sns.barplot(
        data=cat_agg,
        x="category",
        y="total_units_sold",
        hue="category",
        legend=False,
        ax=axes[0],
        palette="Blues_d"
    )

    axes[0].set_title(
        "Total Units Sold by Category",
        fontsize=12,
        fontweight="bold"
    )

    axes[0].set_xlabel("Category")
    axes[0].set_ylabel("Units")

    axes[0].tick_params(
        axis="x",
        rotation=25
    )

    sns.barplot(
        data=cat_agg,
        x="category",
        y="total_revenue",
        hue="category",
        legend=False,
        ax=axes[1],
        palette="Greens_d"
    )

    axes[1].set_title(
        "Total Revenue by Category",
        fontsize=12,
        fontweight="bold"
    )

    axes[1].set_xlabel("Category")
    axes[1].set_ylabel("Revenue ($)")

    axes[1].tick_params(
        axis="x",
        rotation=25
    )

    plt.tight_layout()

    out_file = os.path.join(
        PLOTS_DIR,
        "category_distributions.png"
    )

    plt.savefig(
        out_file,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    logger.info("Saved: %s", out_file)
def plot_stockout_impact(df: pd.DataFrame):
    """
    Plots stockout rate across product categories.
    """

    stockout_stats = (
        df.groupby("category")
        .agg(
            total_days=("stockout_flag", "count"),
            stockout_days=("stockout_flag", "sum")
        )
        .reset_index()
    )

    # Avoid division-by-zero
    stockout_stats["stockout_rate_pct"] = np.where(
        stockout_stats["total_days"] > 0,
        (
            stockout_stats["stockout_days"]
            / stockout_stats["total_days"]
        ) * 100,
        0
    )

    plt.figure(figsize=(9, 4.5))

    sns.barplot(
        data=stockout_stats,
        x="category",
        y="stockout_rate_pct",
        hue="category",
        legend=False,
        palette="Reds_d"
    )

    plt.title(
        "Stock-out Rate (% of Operating Days) by Category",
        fontsize=12,
        fontweight="bold"
    )

    plt.ylabel("Days Out of Stock (%)")
    plt.xlabel("Category")

    plt.tick_params(
        axis="x",
        rotation=20
    )

    plt.tight_layout()

    out_file = os.path.join(
        PLOTS_DIR,
        "stockout_impact.png"
    )

    plt.savefig(
        out_file,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    logger.info("Saved: %s", out_file)

def generate_markdown_report(
    df: pd.DataFrame,
    prod_df: pd.DataFrame
):
   
    total_sales = df["total_units_sold"].sum()

    total_rev = df["total_revenue"].sum()

    total_unfulfilled = df["unfulfilled_demand"].sum()

    stockout_days = df["stockout_flag"].sum()

    total_records = len(df)

    if total_records > 0:
        stockout_pct = (
            stockout_days / total_records
        ) * 100
    else:
        stockout_pct = 0.0


    min_date = df["date"].min()
    max_date = df["date"].max()

    date_range = (
        f"{min_date.strftime('%Y-%m-%d')} "
        f"to "
        f"{max_date.strftime('%Y-%m-%d')}"
    )

    df = df.copy()

    df["dow"] = df["date"].dt.day_name()

    dow_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    dow_stats = (
        df.groupby("dow")["total_units_sold"]
        .mean()
        .reindex(dow_order)
    )

    weekday_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday"
    ]

    weekend_days = [
        "Saturday",
        "Sunday"
    ]

    weekday_mean = dow_stats.loc[
        weekday_days
    ].mean()

    weekend_mean = dow_stats.loc[
        weekend_days
    ].mean()

    if weekday_mean and not pd.isna(weekday_mean):
        weekend_lift = (
            (weekend_mean - weekday_mean)
            / weekday_mean
        ) * 100
    else:
        weekend_lift = 0.0


    promo_df = df[
        df["promotional_flag"] == 1
    ]

    non_promo_df = df[
        df["promotional_flag"] == 0
    ]

    promo_sales = (
        promo_df["total_units_sold"].mean()
        if not promo_df.empty
        else 0.0
    )

    non_promo_sales = (
        non_promo_df["total_units_sold"].mean()
        if not non_promo_df.empty
        else 0.0
    )

    if non_promo_sales != 0:
        promo_lift = (
            (promo_sales - non_promo_sales)
            / non_promo_sales
        ) * 100
    else:
        promo_lift = 0.0

    category_sales = (
        df.groupby("category")["total_units_sold"]
        .sum()
        .sort_values(ascending=False)
    )

    category_revenue = (
        df.groupby("category")["total_revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    top_sales_category = (
        category_sales.index[0]
        if not category_sales.empty
        else "N/A"
    )

    top_revenue_category = (
        category_revenue.index[0]
        if not category_revenue.empty
        else "N/A"
    )

    if total_records > 0:

        avg_unfulfilled_per_record = (
            total_unfulfilled / total_records
        )

    else:

        avg_unfulfilled_per_record = 0.0


    dow_table = (
        dow_stats
        .rename("Average Units Sold")
        .to_frame()
        .round(2)
        .to_markdown()
    )


    report_content = f"""# Exploratory Data Analysis (EDA) Report

**Dataset:** Processed Daily Sales & Inventory  
**Date Range:** {date_range}  
**Catalog Size:** {len(prod_df):,} distinct products  
**Categories:** {prod_df["category"].nunique():,}  
**Observed Product-Days:** {total_records:,}

---

## 1. Executive Summary & KPIs

| KPI | Value |
|---|---:|
| Total Realized Sales | {total_sales:,.0f} units |
| Total Gross Revenue | ${total_rev:,.2f} |
| Total Unfulfilled Demand | {total_unfulfilled:,.0f} units |
| Stock-out Days | {stockout_days:,.0f} |
| Stock-out Frequency | {stockout_pct:.2f}% |
| Average Promotional Lift | {promo_lift:+.1f}% |
| Average Unfulfilled Demand / Product-Day | {avg_unfulfilled_per_record:.2f} units |

### Category Highlights

- **Highest unit-sales category:** {top_sales_category}
- **Highest revenue category:** {top_revenue_category}

---

## 2. Key Patterns & Statistical Findings

### A. Weekly Seasonality — Day-of-Week Effect

Average units sold per product per day:

{dow_table}

**Weekday average:** {weekday_mean:.2f} units

**Weekend average:** {weekend_mean:.2f} units

**Weekend lift vs weekday average:** {weekend_lift:+.1f}%

**Insight:** Weekend demand is approximately **{weekend_lift:.1f}% higher/lower** than the weekday average.

**Feature Engineering Impact:** Day-of-week features may capture recurring demand patterns. For machine-learning models, cyclic encoding using sine/cosine transformations or categorical encoding can be evaluated.

---

### B. Promotional Sensitivity

- **Baseline non-promotional daily average per product:** {non_promo_sales:.2f} units
- **Promotional-event daily average per product:** {promo_sales:.2f} units
- **Observed promotional lift:** {promo_lift:+.1f}%

**Insight:** Promotional days show **{promo_lift:+.1f}% higher/lower average unit sales** than non-promotional days.

This is a descriptive association in the observed dataset and should not be interpreted as a causal estimate of the effect of promotions.

---

### C. The Cost of Inventory Depletion

- **Observed product-days:** {total_records:,}
- **Stock-out product-days:** {stockout_days:,}
- **Stock-out frequency:** {stockout_pct:.2f}%
- **Estimated unfulfilled demand:** {total_unfulfilled:,.0f} units
- **Average unfulfilled demand per product-day:** {avg_unfulfilled_per_record:.2f} units

**Insight:** Inventory availability is directly associated with realized sales and unfulfilled demand in the dataset. Predicting potential stock-outs before inventory reaches zero can therefore be evaluated as a forecasting and inventory-optimization use case.

---

## 3. Visual Artifacts

Generated visualizations are saved under `docs/plots/`.

1. `sales_trend.png`
   - Total daily units sold
   - 30-day moving average
   - Overall sales trajectory

2. `category_distributions.png`
   - Total units sold by category
   - Total revenue by category

3. `stockout_impact.png`
   - Stock-out rate by category

---

## 4. Modeling Considerations

Based on this exploratory analysis, potential predictive-model features include:

- Day of week
- Month
- Promotional flag
- Historical sales
- Rolling sales averages
- Inventory level
- Stock-out history
- Product category
- Product-level demand history
- Seasonal indicators

These features should be evaluated using time-aware validation to avoid leakage from future observations.

---

## 5. Report Generation

This report was automatically generated by:

`pipelines/run_eda.py`

Generated artifacts:

- `docs/eda_report.md`
- `docs/plots/sales_trend.png`
- `docs/plots/category_distributions.png`
- `docs/plots/stockout_impact.png`
"""

    # ========================================================
    # WRITE REPORT
    # ========================================================

    os.makedirs(
        os.path.dirname(REPORT_PATH),
        exist_ok=True
    )

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report_content)

    logger.info(
        "Generated EDA report: %s",
        REPORT_PATH
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # Create output directory
    os.makedirs(
        PLOTS_DIR,
        exist_ok=True
    )

    logger.info(
        "Executing Exploratory Data Analysis..."
    )

    # Load data
    df, prod_df = load_datasets()

    # Generate plots
    plot_sales_trend(df)

    plot_category_distributions(df)

    plot_stockout_impact(df)

    # Generate Markdown report
    generate_markdown_report(
        df,
        prod_df
    )

    print(
        "\n---------------------------------------------------------"
    )

    print(
        "EDA COMPLETE: Markdown report generated at "
        f"'{REPORT_PATH}'."
    )

    print(
        f"Plots saved to '{PLOTS_DIR}'."
    )

    print(
        "---------------------------------------------------------"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
