-- Analytics queries for SupplyPulse inventory database
-- Assumes tables: products, suppliers, inventory, purchase_orders

-- 1) Top 10 highest-risk SKUs (proxy risk score)
-- risk_score = 100 * max(lead_time_demand - inventory_position,0) / (lead_time_demand + 1)
SELECT p.sku, p.product_name, p.category,
       i.on_hand, i.on_order, i.committed,
       i.daily_demand_avg,
       (i.daily_demand_avg * i.lead_time_days) AS lead_time_demand,
       (i.on_hand + i.on_order - i.committed) AS inventory_position,
       ROUND(100.0 * (CASE WHEN (i.daily_demand_avg * i.lead_time_days) <= 0 THEN 0
           ELSE (CASE WHEN (i.daily_demand_avg * i.lead_time_days) - (i.on_hand + i.on_order - i.committed) > 0
                       THEN ((i.daily_demand_avg * i.lead_time_days) - (i.on_hand + i.on_order - i.committed)) / (i.daily_demand_avg * i.lead_time_days)
                       ELSE 0 END)
       END),2) AS risk_score
FROM products p
JOIN inventory i ON p.sku = i.sku
ORDER BY risk_score DESC
LIMIT 10;

-- 2) SKUs below reorder point
-- reorder_point = lead_time_demand + safety_stock (safety_stock ~ 1.645 * std * sqrt(lead_time_days))
SELECT p.sku, p.product_name, p.category,
       i.on_hand, i.on_order, i.committed,
       (i.daily_demand_avg * i.lead_time_days) AS lead_time_demand,
       (1.645 * i.daily_demand_std * sqrt(i.lead_time_days)) AS safety_stock,
       ((i.daily_demand_avg * i.lead_time_days) + (1.645 * i.daily_demand_std * sqrt(i.lead_time_days))) AS reorder_point,
       (i.on_hand + i.on_order - i.committed) AS inventory_position
FROM products p
JOIN inventory i ON p.sku = i.sku
WHERE (i.on_hand + i.on_order - i.committed) < ((i.daily_demand_avg * i.lead_time_days) + (1.645 * i.daily_demand_std * sqrt(i.lead_time_days)))
ORDER BY ((i.daily_demand_avg * i.lead_time_days) + (1.645 * i.daily_demand_std * sqrt(i.lead_time_days))) - (i.on_hand + i.on_order - i.committed) DESC;

-- 3) Overstocked SKUs (days_of_coverage > threshold, threshold = 180 days)
SELECT p.sku, p.product_name, p.category,
       i.on_hand, i.daily_demand_avg,
       ROUND(CASE WHEN i.daily_demand_avg<=0 THEN NULL ELSE i.on_hand / i.daily_demand_avg END,2) AS days_of_coverage
FROM products p
JOIN inventory i ON p.sku = i.sku
WHERE (i.daily_demand_avg > 0) AND (i.on_hand / i.daily_demand_avg) > 180
ORDER BY (i.on_hand / i.daily_demand_avg) DESC;

-- 4) Inventory value by category
SELECT p.category,
       SUM(i.on_hand * p.unit_cost) AS inventory_value,
       SUM(i.on_hand) AS total_units
FROM products p
JOIN inventory i ON p.sku = i.sku
GROUP BY p.category
ORDER BY inventory_value DESC;

-- 5) Average lead time by supplier
SELECT s.name AS supplier, ROUND(AVG(i.lead_time_days),2) AS avg_lead_time_days, COUNT(DISTINCT p.sku) AS sku_count
FROM suppliers s
JOIN products p ON p.supplier_id = s.id
JOIN inventory i ON i.sku = p.sku
GROUP BY s.id
ORDER BY avg_lead_time_days DESC;

-- 6) Demand by category (sum of avg daily demand)
SELECT p.category, SUM(i.daily_demand_avg) AS total_daily_demand, SUM(i.daily_demand_avg * i.lead_time_days) AS total_lead_time_demand
FROM products p
JOIN inventory i ON p.sku = i.sku
GROUP BY p.category
ORDER BY total_daily_demand DESC;

-- 7) Products with highest inventory value
SELECT p.sku, p.product_name, p.category, i.on_hand, p.unit_cost, (i.on_hand * p.unit_cost) AS inventory_value
FROM products p
JOIN inventory i ON p.sku = i.sku
ORDER BY inventory_value DESC
LIMIT 20;

-- 8) Products with lowest days of coverage (at risk of stockout)
SELECT p.sku, p.product_name, i.on_hand, i.daily_demand_avg,
       ROUND(CASE WHEN i.daily_demand_avg <= 0 THEN NULL ELSE (i.on_hand / i.daily_demand_avg) END,2) AS days_of_coverage
FROM products p
JOIN inventory i ON p.sku = i.sku
WHERE i.daily_demand_avg > 0
ORDER BY (i.on_hand / i.daily_demand_avg) ASC
LIMIT 20;

-- 9) Supplier performance summary (open PO volume, avg lead time, total SKU value)
SELECT s.name AS supplier,
       COUNT(DISTINCT p.sku) AS sku_count,
       SUM(CASE WHEN po.status = 'OPEN' THEN po.qty ELSE 0 END) AS open_po_units,
       ROUND(AVG(i.lead_time_days),2) AS avg_lead_time_days,
       ROUND(SUM(i.on_hand * p.unit_cost),2) AS supplier_inventory_value
FROM suppliers s
LEFT JOIN products p ON p.supplier_id = s.id
LEFT JOIN inventory i ON i.sku = p.sku
LEFT JOIN purchase_orders po ON po.sku = p.sku
GROUP BY s.id
ORDER BY open_po_units DESC, supplier_inventory_value DESC;

-- 10) Recommended replenishment quantities by category (sum of recommended_order_qty proxy)
-- recommended_order_qty proxy = MAX(lead_time_demand + safety_stock + avg_daily_demand - inventory_position, 0)
SELECT p.category,
       SUM(
           CASE WHEN ((i.daily_demand_avg * i.lead_time_days) + (1.645 * i.daily_demand_std * sqrt(i.lead_time_days)) + i.daily_demand_avg - (i.on_hand + i.on_order - i.committed)) > 0
           THEN ((i.daily_demand_avg * i.lead_time_days) + (1.645 * i.daily_demand_std * sqrt(i.lead_time_days)) + i.daily_demand_avg - (i.on_hand + i.on_order - i.committed))
           ELSE 0 END
       ) AS total_recommended_qty,
       SUM(i.on_hand) AS total_on_hand
FROM products p
JOIN inventory i ON p.sku = i.sku
GROUP BY p.category
ORDER BY total_recommended_qty DESC;
