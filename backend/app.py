import os
import sys
import sqlite3
import json
from typing import Dict, Any

# Ensure project root is on sys.path so `backend.services` imports work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, jsonify, request, abort
from flask_cors import CORS

# Import inventory engine utilities
from backend.services.inventory_engine import compute_sku_metrics, aggregate_metrics
import pandas as pd

app = Flask(__name__)
CORS(app)

# DB path resolution: prefer backend/inventory.db, then backend/data/inventory.db, then backend/database.db
BASE_DIR = os.path.dirname(__file__)
# Prefer a few common DB locations so the app is resilient across setups
candidates = [
    os.path.join(BASE_DIR, 'inventory.db'),
    os.path.join(BASE_DIR, 'data', 'inventory.db'),
    os.path.join(BASE_DIR, 'database.db'),
]
DB_PATH = None
for p in candidates:
    if os.path.exists(p):
        DB_PATH = p
        break
if DB_PATH is None:
    raise FileNotFoundError(f"Expected database at one of {candidates} — none found.")


def query_df(query: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def load_inventory_snapshot_from_db() -> pd.DataFrame:
    # load inventory table and product fields
    inv = query_df('SELECT * FROM inventory')
    prod = query_df('SELECT sku, product_name, category, unit_cost, supplier_id FROM products')
    df = inv.merge(prod, on='sku', how='left')
    # normalize column names expected by inventory_engine
    df = df.rename(columns={
        'current_stock': 'on_hand',
        'units_on_order': 'on_order',
        'daily_demand_avg': 'avg_daily_demand',
        'daily_demand_std': 'demand_volatility',
    })
    return df


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'db_path': DB_PATH})


@app.route('/api/kpis')
def kpis():
    try:
        inv = load_inventory_snapshot_from_db()
        metrics = compute_sku_metrics(inv)
        agg = aggregate_metrics(metrics)
        return jsonify(agg)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory')
def inventory_list():
    try:
        df = load_inventory_snapshot_from_db()
        # return basic inventory fields
        out = df[['sku', 'product_name', 'category', 'on_hand', 'on_order', 'committed', 'unit_cost']].to_dict(orient='records')
        return jsonify(out)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory/<sku_id>')
def inventory_item(sku_id):
    try:
        df = load_inventory_snapshot_from_db()
        row = df[df['sku'] == sku_id]
        if row.empty:
            return jsonify({'error': 'SKU not found'}), 404
        metrics = compute_sku_metrics(row)
        return jsonify(metrics.to_dict(orient='records')[0])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/risk')
def risk_list():
    try:
        inv = load_inventory_snapshot_from_db()
        metrics = compute_sku_metrics(inv)
        out = metrics[['sku', 'stockout_risk_score', 'stockout_risk_category', 'days_of_coverage']].sort_values('stockout_risk_score', ascending=False)
        return jsonify(out.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recommendations')
def recommendations():
    try:
        inv = load_inventory_snapshot_from_db()
        metrics = compute_sku_metrics(inv)
        out = metrics[['sku', 'recommended_order_qty', 'recommended_action']]
        return jsonify(out.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories')
def categories():
    try:
        prod = query_df('SELECT category, COUNT(*) as sku_count FROM products GROUP BY category')
        return jsonify(prod.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/suppliers')
def suppliers():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''SELECT s.id, s.name, COUNT(p.sku) as sku_count, ROUND(SUM(i.on_hand * p.unit_cost),2) as inventory_value
                       FROM suppliers s
                       LEFT JOIN products p ON p.supplier_id = s.id
                       LEFT JOIN inventory i ON i.sku = p.sku
                       GROUP BY s.id''')
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        conn.close()
        return jsonify([dict(zip(cols, r)) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/demand-trends')
def demand_trends():
    try:
        # Using historical columns if present
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT sku, historical_demand_30d, historical_demand_90d FROM inventory')
        rows = cur.fetchall()
        conn.close()
        return jsonify([{'sku': r[0], 'demand_30d': r[1], 'demand_90d': r[2]} for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)
