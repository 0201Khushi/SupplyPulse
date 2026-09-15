import os
import sqlite3
import csv

WORKDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CSV_PATH = os.path.join(WORKDIR, 'data', 'inventory.csv')
DB_PATH = os.path.join(WORKDIR, 'data', 'inventory.db')

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
    if not os.path.exists(csv_path):
        raise FileNotFoundError(csv_path)

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [ {k.lower(): v for k, v in row.items()} for row in reader ]

    # map aliases
    for r in rows:
        for a, b in ALIAS_MAP.items():
            if a in r and b not in r:
                r[b] = r.get(a)

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    create_schema(conn)
    cur = conn.cursor()

    # suppliers
    suppliers = {}
    for r in rows:
        name = (r.get('supplier') or 'UNKNOWN').strip()
        if name not in suppliers:
            cur.execute('INSERT INTO suppliers (name) VALUES (?)', (name,))
            suppliers[name] = cur.lastrowid

    # products
    prod_rows = []
    for r in rows:
        sku = r.get('sku') or r.get('sku_id')
        if sku is None:
            continue
        sku = str(sku).strip()
        product_name = r.get('product_name')
        category = r.get('category')
        supplier_name = r.get('supplier') or 'UNKNOWN'
        supplier_id = suppliers.get(supplier_name.strip())
        try:
            unit_cost = float(r.get('unit_cost') or 0)
        except Exception:
            unit_cost = 0.0
        prod_rows.append((sku, product_name, category, supplier_id, unit_cost))

    cur.executemany('INSERT OR REPLACE INTO products (sku, product_name, category, supplier_id, unit_cost) VALUES (?,?,?,?,?)', prod_rows)

    inv_rows = []
    po_rows = []
    for r in rows:
        sku = r.get('sku') or r.get('sku_id')
        if sku is None:
            continue
        sku = str(sku).strip()
        def to_int(v, default=0):
            try:
                return int(float(v))
            except Exception:
                return default
        def to_float(v, default=0.0):
            try:
                return float(v)
            except Exception:
                return default
        on_hand = to_int(r.get('on_hand') or r.get('current_stock') or 0)
        on_order = to_int(r.get('on_order') or r.get('units_on_order') or r.get('open_purchase_orders') or 0)
        committed = to_int(r.get('committed') or 0)
        lead_time_days = to_int(r.get('lead_time_days') or 7)
        daily_demand_avg = to_float(r.get('daily_demand_avg') or r.get('daily_demand_avg') or 0)
        daily_demand_std = to_float(r.get('daily_demand_std') or r.get('daily_demand_std') or 0)
        historical_30 = to_int(r.get('historical_demand_30d') or 0)
        historical_90 = to_int(r.get('historical_demand_90d') or 0)
        last_restock = r.get('last_restock_date')
        inv_rows.append((sku, on_hand, on_order, committed, lead_time_days, daily_demand_avg, daily_demand_std, historical_30, historical_90, last_restock))
        if on_order and on_order > 0:
            supplier_name = r.get('supplier') or 'UNKNOWN'
            supplier_id = suppliers.get(supplier_name.strip())
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
    print(f"Loaded {len(rows)} rows into {db_path}")


if __name__ == '__main__':
    load_csv_to_db()
