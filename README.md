# HelloWorld

This repository includes a synthetic data generator for practicing Databricks Machine Learning workflows.

## Databricks ML learning data

Generate a reproducible set of CSV and JSON Lines files with:

- `customers.csv`: customer profile features suitable for feature table practice.
- `sales_orders.csv`: order-level data for regression and binary classification.
- `sales_orders.jsonl`: the same order-level data in JSON Lines format for ingestion practice.
- `daily_product_demand.csv`: daily aggregates for time-series and forecasting exercises.

Run the generator from the repository root:

```bash
python3 scripts/generate_databricks_ml_data.py
```

By default, the data is written to `data/databricks_ml/`. You can change the size or location:

```bash
python3 scripts/generate_databricks_ml_data.py --rows 10000 --customers 1500 --seed 7 --output-dir data/databricks_ml_large
```

### Suggested Databricks ML exercises

1. Upload `data/databricks_ml/sales_orders.csv` to DBFS or a Unity Catalog volume.
2. Use Databricks AutoML to predict `revenue` as a regression target.
3. Use Databricks AutoML to predict `repeat_purchase_90d` as a classification target.
4. Join `sales_orders.csv` with `customers.csv` on `customer_id` to practice feature engineering.
5. Use `daily_product_demand.csv` to build lag features and forecast `units_sold` by `product_name`.
6. Track experiments with MLflow and compare models that use only order features versus joined customer features.

### Example Databricks notebook snippet

```python
from pyspark.sql.functions import col

sales_path = "/Volumes/<catalog>/<schema>/<volume>/sales_orders.csv"
customers_path = "/Volumes/<catalog>/<schema>/<volume>/customers.csv"

sales = spark.read.option("header", True).option("inferSchema", True).csv(sales_path)
customers = spark.read.option("header", True).option("inferSchema", True).csv(customers_path)

training_df = (
    sales.join(customers.drop("customer_segment", "region", "support_tickets_90d", "monthly_site_visits", "satisfaction_score"), "customer_id")
    .withColumn("label", col("repeat_purchase_90d"))
)

display(training_df)
```
