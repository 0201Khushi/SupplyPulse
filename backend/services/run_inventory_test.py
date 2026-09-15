import os
import sys

# Ensure workspace root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.inventory_engine import load_inventory_snapshot, compute_sku_metrics, aggregate_metrics

DATA_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'inventory.csv'))


def main():
    inv = load_inventory_snapshot(DATA_CSV)
    metrics = compute_sku_metrics(inv)
    agg = aggregate_metrics(metrics)
    print("\nAGGREGATED KPIS:")
    for k, v in agg.items():
        print(f"{k}: {v}")

    print("\nTop 10 highest-risk SKUs:")
    top10 = metrics.sort_values('stockout_risk_score', ascending=False).head(10)
    cols = ['sku', 'stockout_risk_score', 'stockout_risk_category', 'recommended_order_qty', 'recommended_action', 'days_of_coverage']
    print(top10[cols].to_string(index=False))


if __name__ == '__main__':
    main()
