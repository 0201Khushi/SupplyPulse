import os
import sqlite3
import re

WORKDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(WORKDIR, 'data', 'inventory.db')
SQL_PATH = os.path.join(WORKDIR, 'sql', 'analytics.sql')


def run_queries(db_path=DB_PATH, sql_path=SQL_PATH):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Basic checks
    results = {}
    cur.execute('SELECT COUNT(*) FROM products')
    results['number_of_skus'] = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM suppliers')
    results['number_of_suppliers'] = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT category) FROM products')
    results['number_of_categories'] = cur.fetchone()[0]
    cur.execute('SELECT SUM(on_hand) FROM inventory')
    results['total_inventory_units'] = int(cur.fetchone()[0] or 0)
    cur.execute('SELECT SUM(i.on_hand * p.unit_cost) FROM inventory i JOIN products p ON i.sku=p.sku')
    v = cur.fetchone()[0]
    results['total_inventory_value'] = float(v or 0.0)

    # Read analytics SQL and execute each query block
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_text = f.read()

    # Split queries by semicolon followed by newline(s)
    raw_parts = [p.strip() for p in re.split(r';\s*\n', sql_text) if p.strip()]

    query_results = []
    errors = []
    for idx, part in enumerate(raw_parts, start=1):
        # Remove leading/trailing comment lines
        lines = [ln for ln in part.splitlines() if not ln.strip().startswith('--')]
        stmt = '\n'.join(lines).strip()
        if not stmt:
            continue
        try:
            cur.execute(stmt)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            query_results.append({'index': idx, 'sql': stmt, 'cols': cols, 'rows': rows})
        except Exception as e:
            errors.append({'index': idx, 'error': str(e), 'sql': stmt[:200]})

    # Extract top 10 highest-risk SKUs from the first query result (if present)
    top10 = []
    if query_results:
        # Find first non-empty result
        for qr in query_results:
            if qr['rows']:
                top10 = qr['rows'][:10]
                top10_cols = qr['cols']
                break

    # Total recommended reorder quantity: sum total_recommended_qty from query 10's result
    total_recommended_qty = None
    # find query containing 'total_recommended_qty' or last query
    for qr in query_results:
        if any('total_recommended_qty' in (c or '').lower() for c in qr['cols']):
            # sum over rows first column that matches name
            col_idx = None
            for i, c in enumerate(qr['cols']):
                if 'total_recommended_qty' in (c or '').lower():
                    col_idx = i
                    break
            if col_idx is None and qr['cols']:
                # fallback: take first numeric column
                col_idx = 0
            if col_idx is not None:
                total_recommended_qty = sum([r[col_idx] or 0 for r in qr['rows']])
                break

    # If not found, attempt to compute via SQL proxy
    if total_recommended_qty is None:
        try:
            cur.execute('''SELECT SUM(CASE WHEN ((i.daily_demand_avg * i.lead_time_days) + (1.645 * i.daily_demand_std * sqrt(i.lead_time_days)) + i.daily_demand_avg - (i.on_hand + i.on_order - i.committed)) > 0 THEN ((i.daily_demand_avg * i.lead_time_days) + (1.645 * i.daily_demand_std * sqrt(i.lead_time_days)) + i.daily_demand_avg - (i.on_hand + i.on_order - i.committed)) ELSE 0 END) FROM products p JOIN inventory i ON p.sku=i.sku''')
            total_recommended_qty = cur.fetchone()[0] or 0
        except Exception:
            total_recommended_qty = 0

    conn.close()

    return {
        'results_summary': results,
        'top10': {'cols': top10_cols if top10 else [], 'rows': top10},
        'total_recommended_reorder_qty': float(total_recommended_qty),
        'all_queries_executed': len(errors) == 0,
        'query_errors': errors,
    }


if __name__ == '__main__':
    out = run_queries()
    print('DATABASE SUMMARY:')
    for k, v in out['results_summary'].items():
        print(f'{k}: {v}')
    print('\nTop 10 highest-risk SKUs:')
    if out['top10']['rows']:
        print('\t' + '\t'.join(out['top10']['cols']))
        for r in out['top10']['rows']:
            print('\t' + '\t'.join([str(x) for x in r]))
    else:
        print('\t(no rows)')
    print('\nTotal recommended reorder quantity:', out['total_recommended_reorder_qty'])
    print('All queries executed successfully:', out['all_queries_executed'])
    if out['query_errors']:
        print('\nErrors:')
        for e in out['query_errors']:
            print(e)
