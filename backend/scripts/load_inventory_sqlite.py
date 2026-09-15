import os
import sqlite3
import pandas as pd

WORKDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CSV_PATH = os.path.join(WORKDIR, 'data', 'inventory.csv')
DB_PATH = os.path.join(WORKDIR, 'data', 'inventory.db')

# Column alias mapping mirrors inventory_engine behavior
ALIAS_MAP = {
    'sku_id': 'sku',
    'current_stock': 'on_hand',
    'units_on_order': 'on_order',
    'open_purchase_orders': 'on_order',
    'daily_demand_avg': 'daily_demand_avg',
    'daily_demand_std': 'daily_demand_std',
}


def create_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript('''
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        supplier_id INTEGER,
        unit_cost REAL,
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
    );

    CREATE TABLE IF NOT EXISTS inventory (
        sku TEXT PRIMARY KEY,
        on_hand INTEGER DEFAULT 0,
        on_order INTEGER DEFAULT 0,
        committed INTEGER DEFAULT 0,
        lead_time_days INTEGER DEFAULT 7,
        daily_demand_avg REAL DEFAULT 0,
        daily_demand_std REAL DEFAULT 0,
        historical_demand_30d INTEGER,
        historical_demand_90d INTEGER,
        last_restock_date TEXT,
        FOREIGN KEY(sku) REFERENCES products(sku)
    );

    CREATE TABLE IF NOT EXISTS purchase_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT,
        qty INTEGER,
        status TEXT,
        created_date TEXT,
        supplier_id INTEGER,
        FOREIGN KEY(sku) REFERENCES products(sku),
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
    );
    ''')
    conn.commit()


def load_csv_to_db(csv_path: str = CSV_PATH, db_path: str = DB_PATH):
    df = pd.read_csv(csv_path)
    # normalize columns
    df.columns = [c.lower() for c in df.columns]
    for a, b in ALIAS_MAP.items():
        if a in df.columns and b not in df.columns:
            df = df.rename(columns={a: b})

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    create_schema(conn)
    cur = conn.cursor()

    # Insert suppliers
    suppliers = df['supplier'].fillna('UNKNOWN').unique()
    supplier_id_map = {}
    for s in suppliers:
        cur.execute('INSERT INTO suppliers (name) VALUES (?)', (s,))
        supplier_id_map[s] = cur.lastrowid

    # Insert products
    prod_rows = []
    for _, r in df.iterrows():
        sku = str(r.get('sku') or r.get('sku_id'))
        product_name = r.get('product_name')
        category = r.get('category')
        supplier = r.get('supplier')
        supplier_id = supplier_id_map.get(supplier)
        unit_cost = float(r.get('unit_cost') or 0)
        prod_rows.append((sku, product_name, category, supplier_id, unit_cost))

    cur.executemany('INSERT OR REPLACE INTO products (sku, product_name, category, supplier_id, unit_cost) VALUES (?,?,?,?,?)', prod_rows)

    # Insert inventory
    inv_rows = []
    po_rows = []
    for _, r in df.iterrows():
        sku = str(r.get('sku') or r.get('sku_id'))
        on_hand = int(r.get('on_hand') or r.get('current_stock') or 0)
        on_order = int(r.get('on_order') or r.get('units_on_order') or r.get('open_purchase_orders') or 0)
        committed = int(r.get('committed') or 0)
        lead_time_days = int(r.get('lead_time_days') or 7)
        daily_demand_avg = float(r.get('daily_demand_avg') or r.get('daily_demand_avg') or r.get('daily_demand_avg') or r.get('daily_demand_avg') or r.get('daily_demand_avg') or 0)
        # try common names
        daily_demand_avg = float(r.get('daily_demand_avg') if pd.notna(r.get('daily_demand_avg')) else r.get('daily_demand_avg') if pd.notna(r.get('daily_demand_avg')) else r.get('daily_demand_avg') if pd.notna(r.get('daily_demand_avg')) else r.get('daily_demand_avg') if pd.notna(r.get('daily_demand_avg')) else r.get('daily_demand_avg') if pd.notna(r.get('daily_demand_avg')) else r.get('daily_demand_avg') if pd.notna(r.get('daily_demand_avg')) else r.get('daily_demand_avg') or r.get('daily_demand_avg') or 0)
        daily_demand_std = float(r.get('daily_demand_std') or r.get('daily_demand_std') or 0)
        historical_30 = int(r.get('historical_demand_30d') or 0)
        historical_90 = int(r.get('historical_demand_90d') or 0)
        last_restock = r.get('last_restock_date')
        inv_rows.append((sku, on_hand, on_order, committed, lead_time_days, daily_demand_avg, daily_demand_std, historical_30, historical_90, last_restock))

        # Create a single open purchase order record when on_order>0
        if on_order and on_order > 0:
            supplier = r.get('supplier')
            supplier_id = supplier_id_map.get(supplier)
            po_rows.append((sku, on_order, 'OPEN', None, supplier_id))

    cur.executemany('''
        INSERT OR REPLACE INTO inventory
        (sku,on_hand,on_order,committed,lead_time_days,daily_demand_avg,daily_demand_std,historical_demand_30d,historical_demand_90d,last_restock_date)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', inv_rows)

    if po_rows:
        cur.executemany('INSERT INTO purchase_orders (sku, qty, status, created_date, supplier_id) VALUES (?,?,?,?,?)', po_rows)

    conn.commit()
    conn.close()
    print(f"Loaded {len(df)} rows into {db_path}")


if __name__ == '__main__':
    load_csv_to_db()
