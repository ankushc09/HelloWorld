#!/usr/bin/env python3
"""Generate synthetic datasets for learning Databricks Machine Learning.

The generated files are intentionally small enough to upload to DBFS or a Unity
Catalog volume, but varied enough to practice common ML workflows: regression,
classification, time-series feature engineering, AutoML, MLflow tracking, and
feature lookups.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

PRODUCTS = [
    ("basic_widget", "consumer", 19.99),
    ("pro_widget", "consumer", 49.99),
    ("team_widget", "business", 129.99),
    ("enterprise_widget", "business", 499.99),
    ("analytics_addon", "business", 89.99),
    ("support_plan", "service", 39.99),
]

REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
CHANNELS = ["web", "mobile", "partner", "retail"]
CUSTOMER_SEGMENTS = ["student", "individual", "small_business", "mid_market", "enterprise"]
CAMPAIGNS = ["none", "spring_sale", "back_to_school", "holiday", "loyalty", "webinar"]
DEVICE_TYPES = ["desktop", "phone", "tablet"]


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def weighted_choice(rng: random.Random, weighted_items: list[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in weighted_items)
    threshold = rng.random() * total
    cumulative = 0.0
    for item, weight in weighted_items:
        cumulative += weight
        if cumulative >= threshold:
            return item
    return weighted_items[-1][0]


def make_customers(rng: random.Random, customer_count: int) -> list[dict[str, object]]:
    customers: list[dict[str, object]] = []
    for idx in range(1, customer_count + 1):
        segment = weighted_choice(
            rng,
            [
                ("student", 0.11),
                ("individual", 0.35),
                ("small_business", 0.25),
                ("mid_market", 0.19),
                ("enterprise", 0.10),
            ],
        )
        region = rng.choice(REGIONS)
        tenure_months = rng.randint(0, 84)
        support_tickets_90d = max(0, int(rng.gauss(1.2 if segment == "enterprise" else 0.7, 1.1)))
        monthly_visits = max(1, int(rng.lognormvariate(2.2, 0.6)))
        satisfaction_score = round(clamp(rng.gauss(7.7, 1.4) - support_tickets_90d * 0.25, 1.0, 10.0), 1)
        email_opt_in = rng.random() < (0.72 if segment in {"individual", "student"} else 0.58)
        customers.append(
            {
                "customer_id": f"C{idx:05d}",
                "customer_segment": segment,
                "region": region,
                "tenure_months": tenure_months,
                "support_tickets_90d": support_tickets_90d,
                "monthly_site_visits": monthly_visits,
                "satisfaction_score": satisfaction_score,
                "email_opt_in": email_opt_in,
            }
        )
    return customers


def make_sales(rng: random.Random, customers: list[dict[str, object]], row_count: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    start_date = date(2024, 1, 1)
    for order_number in range(1, row_count + 1):
        customer = rng.choice(customers)
        product_name, category, base_price = rng.choice(PRODUCTS)
        order_date = start_date + timedelta(days=rng.randint(0, 729))
        day_of_year = order_date.timetuple().tm_yday
        seasonal_factor = 1 + 0.12 * math.sin((day_of_year / 365) * 2 * math.pi)
        campaign = weighted_choice(
            rng,
            [("none", 0.45), ("spring_sale", 0.13), ("back_to_school", 0.10), ("holiday", 0.16), ("loyalty", 0.10), ("webinar", 0.06)],
        )
        channel = weighted_choice(rng, [("web", 0.40), ("mobile", 0.28), ("partner", 0.20), ("retail", 0.12)])
        device_type = rng.choice(DEVICE_TYPES)
        discount_rate = round(
            clamp(
                rng.gauss(0.08, 0.04)
                + (0.08 if campaign in {"spring_sale", "holiday"} else 0.0)
                + (0.03 if customer["customer_segment"] == "enterprise" else 0.0),
                0.0,
                0.35,
            ),
            3,
        )
        quantity_base = 1.0 + (2.5 if customer["customer_segment"] == "enterprise" else 0.0) + (1.2 if category == "business" else 0.0)
        quantity = max(1, int(rng.expovariate(1 / quantity_base)))
        shipping_days = max(1, int(rng.gauss(4.2, 1.4) - (0.7 if customer["region"] == "West" else 0.0)))
        unit_price = round(base_price * seasonal_factor * rng.uniform(0.95, 1.05), 2)
        revenue = round(unit_price * quantity * (1 - discount_rate), 2)
        repeat_purchase_score = (
            0.04 * int(customer["tenure_months"])
            + 0.35 * float(customer["satisfaction_score"])
            + 0.03 * int(customer["monthly_site_visits"])
            - 0.45 * int(customer["support_tickets_90d"])
            + (1.1 if campaign == "loyalty" else 0.0)
            - 3.2
        )
        repeat_purchase_90d = rng.random() < sigmoid(repeat_purchase_score)
        rows.append(
            {
                "order_id": f"O{order_number:06d}",
                "order_date": order_date.isoformat(),
                "customer_id": customer["customer_id"],
                "customer_segment": customer["customer_segment"],
                "region": customer["region"],
                "product_name": product_name,
                "product_category": category,
                "channel": channel,
                "campaign": campaign,
                "device_type": device_type,
                "unit_price": unit_price,
                "quantity": quantity,
                "discount_rate": discount_rate,
                "shipping_days": shipping_days,
                "revenue": revenue,
                "support_tickets_90d": customer["support_tickets_90d"],
                "monthly_site_visits": customer["monthly_site_visits"],
                "satisfaction_score": customer["satisfaction_score"],
                "repeat_purchase_90d": int(repeat_purchase_90d),
            }
        )
    rows.sort(key=lambda row: (row["order_date"], row["order_id"]))
    return rows


def make_daily_demand(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    aggregates: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        key = (str(row["order_date"]), str(row["product_name"]))
        if key not in aggregates:
            aggregates[key] = {
                "date": row["order_date"],
                "product_name": row["product_name"],
                "orders": 0,
                "units_sold": 0,
                "revenue": 0.0,
                "avg_discount_rate": 0.0,
            }
        aggregate = aggregates[key]
        aggregate["orders"] = int(aggregate["orders"]) + 1
        aggregate["units_sold"] = int(aggregate["units_sold"]) + int(row["quantity"])
        aggregate["revenue"] = float(aggregate["revenue"]) + float(row["revenue"])
        aggregate["avg_discount_rate"] = float(aggregate["avg_discount_rate"]) + float(row["discount_rate"])

    daily_rows = []
    for aggregate in aggregates.values():
        orders = int(aggregate["orders"])
        daily_rows.append(
            {
                "date": aggregate["date"],
                "product_name": aggregate["product_name"],
                "orders": orders,
                "units_sold": aggregate["units_sold"],
                "revenue": round(float(aggregate["revenue"]), 2),
                "avg_discount_rate": round(float(aggregate["avg_discount_rate"]) / orders, 3),
            }
        )
    daily_rows.sort(key=lambda row: (row["date"], row["product_name"]))
    return daily_rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as jsonl_file:
        for row in rows:
            jsonl_file.write(json.dumps(row, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic Databricks ML learning datasets.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/databricks_ml"), help="Directory to write datasets into.")
    parser.add_argument("--rows", type=int, default=5000, help="Number of order-level sales rows to generate.")
    parser.add_argument("--customers", type=int, default=750, help="Number of synthetic customers to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible datasets.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.rows < 1:
        raise ValueError("--rows must be at least 1")
    if args.customers < 1:
        raise ValueError("--customers must be at least 1")

    rng = random.Random(args.seed)
    customers = make_customers(rng, args.customers)
    sales = make_sales(rng, customers, args.rows)
    daily_demand = make_daily_demand(sales)

    write_csv(args.output_dir / "customers.csv", customers)
    write_csv(args.output_dir / "sales_orders.csv", sales)
    write_csv(args.output_dir / "daily_product_demand.csv", daily_demand)
    write_jsonl(args.output_dir / "sales_orders.jsonl", sales)

    print(f"Wrote {len(customers):,} customers to {args.output_dir / 'customers.csv'}")
    print(f"Wrote {len(sales):,} sales orders to {args.output_dir / 'sales_orders.csv'} and .jsonl")
    print(f"Wrote {len(daily_demand):,} daily demand rows to {args.output_dir / 'daily_product_demand.csv'}")


if __name__ == "__main__":
    main()
