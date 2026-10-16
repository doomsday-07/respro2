# Executive Tableau Dashboard Blueprint & Implementation Guide
**Project:** Realtime Sales Performance & Inventory Optimization Dashboard  
**Author:** Senior Business Intelligence & Analytics Engineer  
**Workbook:** `Retail_Sales_Inventory_Pulse.twb`  

---

## 1. Executive Architecture & Objectives
This Tableau solution delivers an executive-level view of retail sales performance, gross profitability, and inventory replenishment efficiency across multi-store locations. It empowers store managers and retail executives to:
1. **Detect Demand Spikes:** Real-time statistical alerts (Z-Score $\ge 2.5$) flagging flash sales, social virality, and regional surges.
2. **Eliminate Stockouts (18% Reduction Target):** Predictive Days of Inventory on Hand (DOH) combined with dynamic safety stock buffers preventing critical stockouts before supplier replenishment cycles.
3. **Optimize Working Capital:** Monitor Sell-Through Rate (STR) and Inventory Turnover Ratio (ITR) to balance stock availability against inventory carrying cost.

---

## 2. Data Sources & Schema Connections
The dashboard connects seamlessly to either **PostgreSQL** or the automated extracted files in `data/exports/`:

| Tableau Data Source | File / Table | Grain / Description |
| :--- | :--- | :--- |
| **Retail Sales Mart** | `tableau_retail_mart.csv` / `fact_sales_transactions` | Granular transactional grain with Store & Product dimension attributes. |
| **Daily KPI Mart** | `tableau_daily_kpis.csv` / `fact_kpi_snapshots` | Pre-aggregated daily store-category performance snapshot. |
| **Inventory Health** | `tableau_inventory_health.csv` / `fact_daily_inventory` | Daily inventory levels, stockout flags, and buffer risk scores. |
| **Anomaly Audit** | `tableau_anomalies.csv` / `fact_anomaly_events` | Machine learning & statistical anomaly detection log. |

---

## 3. Core Calculated Fields & Formulas

### A. Sell-Through Rate (STR %)
```tableau
// Sell-Through Rate % = Units Sold / (Beginning Inventory + Units Received)
ZN(SUM([Units Sold])) / 
(ZN(SUM([Units Sold])) + ZN(AVG([Lead Time Days] * 12))) * 100
```

### B. Gross Margin % (Achieved vs Target)
```tableau
// Gross Margin %
(SUM([Gross Revenue]) - SUM([Cogs])) / NULLIF(SUM([Gross Revenue]), 0) * 100
```

### C. Annualized Inventory Turnover Ratio (ITR)
```tableau
// Inventory Turnover = (Annualized COGS) / (Average Inventory Investment)
(SUM([Cogs]) * 2.0) / NULLIF(AVG([Unit Cost] * 65.0), 0)
```

### D. Stockout Risk Indicator & Early Warning
```tableau
// Level of Detail (LOD) expression for store-product velocity
IF [Ending Inventory] = 0 THEN
    "LEVEL 1: Active Stockout"
ELSEIF [Ending Inventory] <= [Lead Time Days] * 2 THEN
    "LEVEL 2: Critical Reorder Alert (18% Reduction Target)"
ELSE
    "LEVEL 3: Healthy Safety Buffer"
END
```

### E. Demand Surge Flag (Z-Score >= 2.5)
```tableau
IF [Units Sold] >= 8 THEN
    "Demand Surge Spike (Flash Sale)"
ELSE
    "Baseline Operational Velocity"
END
```

---

## 4. Visual Layout & Color Palettes

### Executive Color System
* **Primary Executive Navy:** `#0F172A` (Background & Header Containers)
* **Electric Blue (Revenue Accent):** `#3B82F6`
* **Emerald Green (Profitability & Target Met):** `#10B981`
* **Amber Yellow (Reorder Caution):** `#F59E0B`
* **Crimson Alert (Stockout / Anomaly Surge):** `#EF4444`

---

## 5. Automated Refresh Setup
1. **Tableau Desktop / Prep:** Link data connection to `data/exports/tableau_retail_mart.csv` or direct PostgreSQL connection string:
   `postgresql://postgres:postgres@localhost:5432/retail_bi`
2. **Tableau Server / Cloud Schedule:** Set an hourly or daily extract refresh task triggering `python run.py --etl --tableau`.
