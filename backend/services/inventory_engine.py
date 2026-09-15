import math
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
from scipy.stats import norm

__all__ = [
    "load_sales_timeseries",
    "load_inventory_snapshot",
    "compute_sku_metrics",
    "aggregate_metrics",
]


def load_sales_timeseries(path: str, date_col: str = "date", sku_col: str = "sku", qty_col: str = "quantity") -> pd.DataFrame:
    """Load sales/consumption timeseries CSV.

    Expects rows with a date, sku, and quantity (consumed). Returns a DataFrame with
    daily aggregated demand per SKU with a DateTimeIndex.
    """
    df = pd.read_csv(path)
    if date_col not in df.columns or sku_col not in df.columns or qty_col not in df.columns:
        raise ValueError(f"Timeseries file must contain columns: {date_col}, {sku_col}, {qty_col}")
    df[date_col] = pd.to_datetime(df[date_col])
    df = df[[date_col, sku_col, qty_col]].copy()
    df = df.groupby([sku_col, pd.Grouper(key=date_col, freq="D")])[qty_col].sum().reset_index()
    df = df.rename(columns={date_col: "date", sku_col: "sku", qty_col: "quantity"})
    return df


def load_inventory_snapshot(path: str) -> pd.DataFrame:
    """Load an inventory snapshot CSV.

    Required column: `sku`.
    Optional columns: `on_hand`, `on_order`, `committed`, `unit_cost`, `lead_time_days`, `avg_daily_demand`.
    Missing numeric columns will be filled with sensible defaults (0 for quantities, 7 for lead time).
    """
    df = pd.read_csv(path)
    if "sku" not in df.columns:
        raise ValueError("Inventory snapshot must contain a 'sku' column")
    df = df.rename(columns={
        c: c.lower() for c in df.columns
    })
    # Map common CSV column name aliases to the expected normalized names
    alias_map = {
        "sku_id": "sku",
        "current_stock": "on_hand",
        "units_on_order": "on_order",
        "open_purchase_orders": "on_order",
        "daily_demand_avg": "avg_daily_demand",
        "daily_demand_std": "demand_volatility",
        "demand_std": "demand_volatility",
        "unitprice": "unit_cost",
        "price": "unit_cost",
    }
    for a, b in alias_map.items():
        if a in df.columns and b not in df.columns:
            df = df.rename(columns={a: b})

    # Normalize expected column names
    expected = {
        "on_hand": 0,
        "on_order": 0,
        "committed": 0,
        "unit_cost": 0.0,
        "lead_time_days": 7,
        "avg_daily_demand": np.nan,
        "demand_volatility": np.nan,
    }
    for col, default in expected.items():
        if col not in df.columns:
            df[col] = default
    # Ensure numeric types
    for c in ["on_hand", "on_order", "committed", "unit_cost", "lead_time_days", "avg_daily_demand"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["sku"] = df["sku"].astype(str)
    return df


def _z_from_service_level(service_level: float) -> float:
    """Return z-score for a desired service level (e.g., 0.95 -> ~1.645).

    Accepts service_level in (0,1).
    """
    if not (0 < service_level < 1):
        raise ValueError("service_level must be between 0 and 1")
    return float(norm.ppf(service_level))


def compute_sku_metrics(
    inventory_df: pd.DataFrame,
    sales_ts: Optional[pd.DataFrame] = None,
    lead_time_default: int = 7,
    service_level: float = 0.95,
    min_order_qty: int = 0,
    review_period_days: int = 1,
    overstock_days_threshold: int = 180,
) -> pd.DataFrame:
    """Compute per-SKU inventory and replenishment metrics.

    Parameters:
    - `inventory_df`: snapshot as returned by `load_inventory_snapshot` (must include `sku`).
    - `sales_ts`: optional timeseries from `load_sales_timeseries` (columns `sku`,`date`,`quantity`). If provided,
      average daily demand and daily std dev are computed from it. Otherwise `inventory_df` must include
      `avg_daily_demand` and `demand_volatility` (std) or those will be inferred as 0.
    - `lead_time_default`: default lead time in days used when a SKU doesn't specify `lead_time_days`.
    - `service_level`: desired fill/service level used to compute safety stock.
    - `min_order_qty`: floor for recommended order quantities.
    - `review_period_days`: for target inventory calculation (period between reviews)
    - `overstock_days_threshold`: days of coverage above which a SKU is considered overstocked.

    Returns a DataFrame with one row per SKU and these columns (non-exhaustive):
    `avg_daily_demand, demand_volatility, days_of_coverage, lead_time_demand, safety_stock, reorder_point,
     inventory_position, stockout_risk_score, stockout_risk_category, recommended_order_qty, recommended_action`
    """
    df = inventory_df.copy()
    df = df.set_index("sku", drop=False)

    # Prepare demand stats
    demand_mu = pd.Series(dtype=float)
    demand_sigma = pd.Series(dtype=float)
    if sales_ts is not None:
        # Aggregate sales_ts into daily series per sku
        ts = sales_ts.copy()
        ts["date"] = pd.to_datetime(ts["date"]) if ts["date"].dtype != "datetime64[ns]" else ts["date"]
        daily = ts.groupby(["sku", "date"]).quantity.sum().reset_index()
        stats = daily.groupby("sku").quantity.agg(["mean", "std"]).rename(columns={"mean": "mu", "std": "sigma"})
        demand_mu = stats["mu"].reindex(df.index).fillna(0)
        demand_sigma = stats["sigma"].reindex(df.index).fillna(0)
    else:
        # Use columns if present
        if "avg_daily_demand" in df.columns:
            demand_mu = df["avg_daily_demand"].fillna(0)
        else:
            demand_mu = pd.Series(0, index=df.index)
        if "demand_volatility" in df.columns:
            demand_sigma = df["demand_volatility"].fillna(0)
        else:
            demand_sigma = pd.Series(0, index=df.index)

    df["avg_daily_demand"] = demand_mu.astype(float)
    df["demand_volatility"] = demand_sigma.astype(float)

    # Lead time
    if "lead_time_days" not in df.columns:
        df["lead_time_days"] = lead_time_default
    df["lead_time_days"] = df["lead_time_days"].fillna(lead_time_default)

    # Basic metrics
    df["days_of_coverage"] = df.apply(lambda r: math.inf if r["avg_daily_demand"] <= 0 else r["on_hand"] / r["avg_daily_demand"], axis=1)
    df["lead_time_demand"] = df["avg_daily_demand"] * df["lead_time_days"]

    # Safety stock using formula: z * sigma_daily * sqrt(lead_time)
    z = _z_from_service_level(service_level)
    df["safety_stock"] = z * df["demand_volatility"] * np.sqrt(df["lead_time_days"])

    df["reorder_point"] = df["lead_time_demand"] + df["safety_stock"]

    # Inventory position = on_hand + on_order - committed
    for c in ["on_hand", "on_order", "committed"]:
        if c not in df.columns:
            df[c] = 0
    df["inventory_position"] = df["on_hand"].fillna(0) + df["on_order"].fillna(0) - df["committed"].fillna(0)

    # Stockout probability approximated by normal distribution during lead time
    sigma_lt = df["demand_volatility"] * np.sqrt(df["lead_time_days"]).replace(0, np.nan)
    # If sigma_lt is 0 (no variability), then stockout if inventory_position < lead_time_demand -> prob 1 else 0
    z_score = (df["inventory_position"] - df["lead_time_demand"]) / sigma_lt
    stockout_prob = 1 - norm.cdf(z_score.fillna(-np.inf))
    # If sigma_lt was zero, handle explicitly
    zero_var_mask = sigma_lt.isna()
    stockout_prob.loc[zero_var_mask] = np.where(df.loc[zero_var_mask, "inventory_position"] < df.loc[zero_var_mask, "lead_time_demand"], 1.0, 0.0)

    df["stockout_risk_score"] = (stockout_prob * 100).clip(0, 100)

    def risk_category(score: float) -> str:
        if score >= 75:
            return "Critical"
        if score >= 50:
            return "High"
        if score >= 25:
            return "Medium"
        return "Low"

    df["stockout_risk_category"] = df["stockout_risk_score"].map(risk_category)

    # Recommended order quantity: bring to target inventory
    # Target = lead_time_demand + safety_stock + avg_daily_demand * review_period_days
    df["target_inventory"] = df["lead_time_demand"] + df["safety_stock"] + df["avg_daily_demand"] * review_period_days
    df["recommended_order_qty"] = (df["target_inventory"] - df["inventory_position"]).clip(lower=0).apply(np.ceil).fillna(0).astype(int)
    if min_order_qty > 0:
        df["recommended_order_qty"] = df["recommended_order_qty"].apply(lambda q: q if q >= min_order_qty or q == 0 else min_order_qty)

    # Recommended action
    def recommend_action(row: pd.Series) -> str:
        q = int(row["recommended_order_qty"]) if not pd.isna(row["recommended_order_qty"]) else 0
        cat = row["stockout_risk_category"]
        if q > 0 and cat in ("Critical", "High"):
            return "Order Now"
        if q > 0 and cat == "Medium":
            return "Reorder Soon"
        if q > 0 and cat == "Low":
            return "Monitor"
        return "No Action"

    df["recommended_action"] = df.apply(recommend_action, axis=1)

    # Overstock flag
    df["is_overstocked"] = df["days_of_coverage"] > overstock_days_threshold

    # Fulfillment-related approximation metrics
    # fill_rate_estimate: proxy = 1 - average stockout probability (cap 0..1)
    df["fill_rate_estimate"] = (1 - stockout_prob).clip(0, 1)

    # Select and order columns for return
    cols = [
        "sku",
        "on_hand",
        "on_order",
        "committed",
        "unit_cost",
        "avg_daily_demand",
        "demand_volatility",
        "days_of_coverage",
        "lead_time_days",
        "lead_time_demand",
        "safety_stock",
        "reorder_point",
        "inventory_position",
        "stockout_risk_score",
        "stockout_risk_category",
        "recommended_order_qty",
        "recommended_action",
        "is_overstocked",
        "fill_rate_estimate",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan

    result = df[cols].reset_index(drop=True)
    return result


def aggregate_metrics(metrics_df: pd.DataFrame) -> Dict[str, Any]:
    """Return aggregated inventory KPIs from the per-SKU metrics DataFrame.

    Returns a dictionary with keys:
    - total_skus
    - total_inventory_units
    - inventory_value
    - average_days_of_coverage
    - number_critical_skus
    - number_high_risk_skus
    - number_overstocked_skus
    - total_recommended_reorder_qty
    - average_lead_time
    - avg_fill_rate_estimate
    """
    m = metrics_df.copy()
    total_skus = int(m["sku"].nunique())
    total_inventory_units = float(m["on_hand"].fillna(0).sum())
    inventory_value = float((m["on_hand"].fillna(0) * m["unit_cost"].fillna(0)).sum())
    avg_days_coverage = float(m["days_of_coverage"].replace([np.inf, -np.inf], np.nan).dropna().mean()) if not m.empty else 0.0
    number_critical = int((m["stockout_risk_category"] == "Critical").sum())
    number_high = int((m["stockout_risk_category"] == "High").sum())
    number_overstocked = int(m["is_overstocked"].sum())
    total_recommended_reorder_qty = int(m["recommended_order_qty"].fillna(0).sum())
    avg_lead_time = float(m["lead_time_days"].fillna(np.nan).dropna().mean()) if "lead_time_days" in m.columns else float(np.nan)
    avg_fill_rate = float(m["fill_rate_estimate"].dropna().mean()) if "fill_rate_estimate" in m.columns else float(np.nan)

    return {
        "total_skus": total_skus,
        "total_inventory_units": total_inventory_units,
        "inventory_value": inventory_value,
        "average_days_of_coverage": avg_days_coverage,
        "number_critical_skus": number_critical,
        "number_high_risk_skus": number_high,
        "number_overstocked_skus": number_overstocked,
        "total_recommended_reorder_quantity": total_recommended_reorder_qty,
        "average_lead_time": avg_lead_time,
        "avg_fill_rate_estimate": avg_fill_rate,
    }
