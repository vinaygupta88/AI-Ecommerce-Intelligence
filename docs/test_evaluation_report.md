# Test Set Evaluation & Benchmark Report
**Evaluation Period:** 2024-10-01 to 2024-12-23 (Q4 Holiday Quarter)  
**Total Test Observations:** 4,200 SKU-days  

---

## 1. Demand Forecasting Performance (Regression)
Evaluating LightGBM champion model against Naive 7-Day Moving Average Baseline:

| Metric | Champion Model (LightGBM) | Naive Benchmark | Delta / Improvement |
| :--- | :--- | :--- | :--- |
| **WAPE** | **0.1181** (11.81%) | 0.2008 (20.08%) | **-8.26%** |
| **MAE** | **26.05 units** | 44.27 units | **-18.22 units** |
| **RMSE** | **35.54 units** | -- | -- |

*Key finding:* The champion model outperforms the rolling baseline across all error metrics on the unseen Q4 quarter.

---

## 2. Stock-Out Risk Classification Performance
Evaluating XGBoost with class-imbalance weight (`scale_pos_weight` = 2.92):

* **ROC-AUC:** 0.8901
* **PR-AUC (Average Precision):** 0.9023
* **True Positives (Predicted Stockout, Actual Stockout):** 2229
* **False Negatives (Missed Stockouts):** 174
* **False Positives (False Alarms):** 701
* **True Negatives (Correct In-Stock):** 1096
* **Recall (Sensitivity):** 92.76%
* **Precision:** 76.08%

*Supply Chain Analysis:* High recall ensures that over 80% of impending out-of-stock incidents are flagged before they occur.

---

## 3. Anomaly Detection Summary
* **Flagged Abnormal Days:** 334 of 4200 (7.95%)
* Flags indicate high-volume discount shocks and severe zero-supply inventory drops.
