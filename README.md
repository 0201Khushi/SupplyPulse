# SupplyPulse — Inventory & Replenishment Intelligence

> A data-driven inventory intelligence platform that helps teams identify stockout risks, monitor inventory health, and prioritize replenishment decisions across 500+ SKUs.




## 🎯 Problem

Inventory teams often have to manually analyze large SKU catalogs to identify:

- Which products are approaching stockout?
- When should inventory be reordered?
- How much should be reordered?
- Which SKUs are overstocked?
- Which categories hold the most inventory value?
- Which suppliers have longer lead times?

SupplyPulse turns these raw inventory signals into actionable replenishment insights.

---

## 💡 Solution

SupplyPulse combines **inventory analytics, replenishment logic, SQL analysis, and an interactive dashboard** to help prioritize inventory decisions.

The product focuses on three questions:

**What is happening?**  
→ Inventory and demand KPIs

**What needs attention?**  
→ Stockout risk and inventory coverage

**What should I do?**  
→ Replenishment recommendations

---

## ✨ Key Features

### 📦 Inventory Intelligence
- Tracks 1,000 SKUs across 10 categories and 18 suppliers
- Monitors current stock, inventory position, demand, lead time, and inventory coverage
- Calculates inventory value and demand metrics

### ⚠️ Stockout Risk Analysis
- SKU-level risk scoring
- Demand volatility analysis
- Lead-time consideration
- Inventory coverage monitoring
- Risk classification: Critical / High / Medium / Low

### 🔄 Replenishment Engine
Calculates:
- Lead-time demand
- Safety stock
- Reorder point
- Inventory position
- Recommended order quantity
- Recommended replenishment action

Actions include:

`Order Now` · `Reorder Soon` · `Monitor` · `No Action`

### 📊 Analytics Dashboard
- Inventory KPI cards
- Risk distribution
- Inventory by category
- Critical SKU table
- Replenishment recommendations
- SKU-level inventory information

### 🗃️ SQL Analytics
Includes analytical queries for:
- Highest-risk SKUs
- SKUs below reorder point
- Overstocked inventory
- Inventory value by category
- Supplier lead times
- Category demand
- Highest inventory-value products
- Lowest inventory coverage
- Supplier performance
- Recommended replenishment quantities

---

## 📈 Dataset

The application is currently validated against a synthetic inventory dataset:

| Metric | Value |
|---|---:|
| SKUs | 1,000 |
| Suppliers | 18 |
| Categories | 10 |
| Inventory Units | 1,011,161 |
| Inventory Value | ~$40.25M |
| SQL Analytics Queries | 10 |

The dataset contains varied demand, inventory, supplier lead-time, and stock-risk scenarios to simulate realistic inventory-management conditions.

---

## 🧠 Replenishment Logic

SupplyPulse uses explainable inventory-management logic.

```text
Average Demand
      ↓
Demand Variability
      ↓
Supplier Lead Time
      ↓
Lead-Time Demand
      ↓
Safety Stock
      ↓
Reorder Point
      ↓
Inventory Position
      ↓
Stockout Risk
      ↓
Recommended Order Quantity
      ↓
Recommended Action
