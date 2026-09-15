import json

inv_path='backend_debug_inventory.json'
tr_path='backend_debug_trends.json'

def load(path):
    with open(path,'rb') as f:
        b=f.read()
    try:
        s=b.decode('utf-8')
    except UnicodeDecodeError:
        s=b.decode('utf-16')
    return json.loads(s)

inv = load(inv_path)
tr = load(tr_path)
# inv may be object with value key
if isinstance(inv, dict) and 'value' in inv:
    inv_list = inv['value']
else:
    inv_list = inv
if isinstance(tr, dict) and 'value' in tr:
    tr_list = tr['value']
else:
    tr_list = tr

trend_map = {t['sku']: t for t in tr_list}

enriched=[]
for r in inv_list:
    sku=r.get('sku')
    tr=trend_map.get(sku,{})
    demand30 = tr.get('demand_30d') or tr.get('historical_demand_30d') or 0
    daily = demand30/30 if demand30 else 0
    on_hand = float(r.get('on_hand') or 0)
    unit_cost = float(r.get('unit_cost') or 0)
    days = on_hand/daily if daily>0 else float('inf')
    inv_value=on_hand*unit_cost
    enriched.append({'sku':sku,'on_hand':on_hand,'unit_cost':unit_cost,'days':days,'inv_value':inv_value})

total_skus=len(enriched)
inv_value=sum(e['inv_value'] for e in enriched)
total_units=sum(e['on_hand'] for e in enriched)
finite_days=[e['days'] for e in enriched if e['days']!=float('inf')]
avg_cov=sum(finite_days)/len(finite_days) if finite_days else None

print('total_skus=',total_skus)
print('inventory_value=',inv_value)
print('total_units=',total_units)
print('average_days_of_coverage=',avg_cov)

critical=sum(1 for e in enriched if (e['days']!=float('inf') and e['days']<7))
high=sum(1 for e in enriched if (e['days']!=float('inf') and 7<=e['days']<30))
print('critical=',critical,'high=',high)
