from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker("en_GB")


@dataclass(frozen=True)
class Config:
    seed: int = 42
    n_customers: int = 600
    n_products: int = 120
    n_orders: int = 25000
    start_date: str = "2024-01-01"
    end_date: str = "2025-12-31"
    out_dir: str = "data/raw"


def _date_range(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(start=pd.to_datetime(start), end=pd.to_datetime(end), freq="D")


def _weighted_choice(
    items: list[str], weights: list[float], size: int, rng: np.random.Generator
) -> np.ndarray:
    w = np.array(weights, dtype=float)
    w = w / w.sum()
    return rng.choice(items, size=size, replace=True, p=w)


def main() -> None:
    cfg = Config()
    os.makedirs(cfg.out_dir, exist_ok=True)

    rng = np.random.default_rng(cfg.seed)

    # --- Customers ---
    segments = ["SMB", "Mid-Market", "Enterprise"]
    seg_weights = [0.65, 0.25, 0.10]
    customer_ids = [f"C{str(i).zfill(5)}" for i in range(1, cfg.n_customers + 1)]
    customers = []
    for cid, seg in zip(customer_ids, _weighted_choice(segments, seg_weights, cfg.n_customers, rng)):
        customers.append(
            {
                "customer_id": cid,
                "customer_name": fake.company(),
                "segment": seg,
                "country": _weighted_choice(["UK", "IE", "DE", "FR", "NL"], [0.65, 0.10, 0.10, 0.08, 0.07], 1, rng)[0],
                "created_at": fake.date_between(start_date="-5y", end_date="today").isoformat(),
            }
        )
    df_customers = pd.DataFrame(customers)

    # --- Products ---
    categories = ["Consumables", "Equipment", "Parts", "Subscriptions"]
    cat_weights = [0.40, 0.25, 0.25, 0.10]
    product_ids = [f"P{str(i).zfill(4)}" for i in range(1, cfg.n_products + 1)]
    products = []
    for pid, cat in zip(product_ids, _weighted_choice(categories, cat_weights, cfg.n_products, rng)):
        base_price = {
            "Consumables": rng.uniform(8, 40),
            "Parts": rng.uniform(15, 120),
            "Equipment": rng.uniform(250, 2500),
            "Subscriptions": rng.uniform(50, 400),
        }[cat]
        products.append(
            {
                "product_id": pid,
                "product_name": f"{cat} - {fake.word().capitalize()} {fake.word().capitalize()}",
                "category": cat,
                "unit_price": round(float(base_price), 2),
                "unit_cost": round(float(base_price * rng.uniform(0.45, 0.75)), 2),
                "is_active": int(rng.random() > 0.02),
            }
        )
    df_products = pd.DataFrame(products)

    # --- Orders (fact) ---
    channels = ["Direct", "Partner", "Online"]
    channel_weights = [0.45, 0.35, 0.20]
    regions = ["London", "Midlands", "North", "Scotland", "Wales", "NI"]
    region_weights = [0.35, 0.20, 0.20, 0.12, 0.08, 0.05]

    days = _date_range(cfg.start_date, cfg.end_date)
    order_dates = rng.choice(days, size=cfg.n_orders, replace=True)
    order_dates = pd.to_datetime(order_dates)

    order_ids = [f"O{str(i).zfill(7)}" for i in range(1, cfg.n_orders + 1)]
    chosen_customers = rng.choice(customer_ids, size=cfg.n_orders, replace=True)
    chosen_channels = _weighted_choice(channels, channel_weights, cfg.n_orders, rng)
    chosen_regions = _weighted_choice(regions, region_weights, cfg.n_orders, rng)

    # target ship date typically 1-7 days after order
    target_ship_days = rng.integers(1, 8, size=cfg.n_orders)
    target_ship_date = order_dates + pd.to_timedelta(target_ship_days, unit="D")

    # actual ship date: some late, some early
    ship_slip = rng.normal(loc=0.5, scale=1.8, size=cfg.n_orders)  # positive means later
    ship_slip = np.clip(ship_slip, -2.0, 10.0)
    actual_ship_date = target_ship_date + pd.to_timedelta(ship_slip.round().astype(int), unit="D")

    # delivery date typically 1-5 days after ship
    delivery_days = rng.integers(1, 6, size=cfg.n_orders)
    delivery_date = actual_ship_date + pd.to_timedelta(delivery_days, unit="D")

    # order status / cancellations
    cancelled = rng.random(cfg.n_orders) < 0.03
    delivered = ~cancelled

    # order lines: 1-6 per order
    line_counts = rng.integers(1, 7, size=cfg.n_orders)

    rows = []
    for i in range(cfg.n_orders):
        oid = order_ids[i]
        n_lines = int(line_counts[i])
        prods = rng.choice(product_ids, size=n_lines, replace=False if n_lines <= len(product_ids) else True)
        qty = rng.integers(1, 15, size=n_lines)

        for j in range(n_lines):
            rows.append(
                {
                    "order_id": oid,
                    "order_date": order_dates[i].date().isoformat(),
                    "customer_id": chosen_customers[i],
                    "channel": chosen_channels[i],
                    "region": chosen_regions[i],
                    "product_id": prods[j],
                    "quantity": int(qty[j]),
                    "target_ship_date": target_ship_date[i].date().isoformat(),
                    "ship_date": (actual_ship_date[i].date().isoformat() if delivered[i] else None),
                    "delivery_date": (delivery_date[i].date().isoformat() if delivered[i] else None),
                    "is_cancelled": int(cancelled[i]),
                }
            )

    df_order_lines = pd.DataFrame(rows)

    # --- Write CSVs ---
    df_customers.to_csv(os.path.join(cfg.out_dir, "customers.csv"), index=False)
    df_products.to_csv(os.path.join(cfg.out_dir, "products.csv"), index=False)
    df_order_lines.to_csv(os.path.join(cfg.out_dir, "order_lines.csv"), index=False)

    print("✅ Wrote:")
    print(f"- {cfg.out_dir}/customers.csv  ({len(df_customers):,} rows)")
    print(f"- {cfg.out_dir}/products.csv   ({len(df_products):,} rows)")
    print(f"- {cfg.out_dir}/order_lines.csv ({len(df_order_lines):,} rows)")


if __name__ == "__main__":
    main()
