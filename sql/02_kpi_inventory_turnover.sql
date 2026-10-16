-- ==============================================================================
-- Query 02: Inventory Turnover Ratio (ITR) & Days of Inventory on Hand (DOH)
-- Computes capital efficiency, inventory turns, and days of supply remaining.
-- Formula: ITR = (Annualized Cost of Goods Sold) / (Average Inventory Value)
-- Formula: DOH = (Current Inventory Value) / (Average Daily COGS)
-- ==============================================================================

WITH store_inventory_aggregates AS (
    SELECT
        inv.store_id,
        st.name AS store_name,
        st.store_type,
        p.category,
        p.product_id,
        p.product_name,
        p.unit_cost,
        p.list_price,
        -- Aggregate over 90-day evaluation window
        COUNT(DISTINCT inv.snapshot_date) AS total_tracked_days,
        SUM(inv.units_sold) AS total_units_sold,
        SUM(inv.units_sold * p.unit_cost) AS total_cogs,
        SUM(inv.units_sold * p.list_price) AS total_gross_revenue,
        AVG(inv.ending_inventory) AS avg_units_on_hand,
        AVG(inv.inventory_value) AS avg_inventory_value,
        -- Current latest inventory snapshot
        MAX(inv.ending_inventory) AS latest_stock_units,
        MAX(inv.inventory_value) AS latest_stock_value
    FROM fact_daily_inventory inv
    JOIN dim_stores st ON inv.store_id = st.store_id
    JOIN dim_products p ON inv.product_id = p.product_id
    GROUP BY
        inv.store_id, st.name, st.store_type,
        p.category, p.product_id, p.product_name,
        p.unit_cost, p.list_price
),

turnover_computation AS (
    SELECT
        store_id,
        store_name,
        store_type,
        category,
        product_id,
        product_name,
        total_units_sold,
        total_cogs,
        total_gross_revenue,
        avg_units_on_hand,
        avg_inventory_value,
        latest_stock_units,
        latest_stock_value,
        -- Daily COGS Run-rate
        (total_cogs / NULLIF(total_tracked_days, 0)) AS daily_cogs_burn,
        -- Annualized Inventory Turnover Ratio
        ROUND(
            CASE
                WHEN avg_inventory_value > 0
                THEN (total_cogs * (365.0 / NULLIF(total_tracked_days, 0))) / avg_inventory_value
                ELSE 0.0
            END, 2
        ) AS annualized_inventory_turnover,
        -- Days of Inventory on Hand (DOH)
        ROUND(
            CASE
                WHEN (total_cogs / NULLIF(total_tracked_days, 0)) > 0
                THEN latest_stock_value / (total_cogs / total_tracked_days)
                ELSE 999.0
            END, 1
        ) AS days_of_inventory_on_hand
    FROM store_inventory_aggregates
)

SELECT
    store_name,
    store_type,
    category,
    product_name,
    ROUND(total_gross_revenue, 2) AS gross_revenue,
    ROUND(total_cogs, 2) AS total_cogs,
    ROUND(avg_inventory_value, 2) AS avg_inventory_value,
    annualized_inventory_turnover AS inventory_turns,
    days_of_inventory_on_hand AS doh_days,
    -- Inventory Health & Capital Efficiency Segment
    CASE
        WHEN days_of_inventory_on_hand < 10.0 THEN 'High Stockout Exposure (Critical Low)'
        WHEN days_of_inventory_on_hand BETWEEN 10.0 AND 30.0 THEN 'Optimal Lean Buffer'
        WHEN days_of_inventory_on_hand BETWEEN 30.1 AND 60.0 THEN 'Moderate Holding Stock'
        ELSE 'Excess Capital Allocation (Overstocked)'
    END AS inventory_health_status,
    -- Dense Rank by inventory turnover efficiency
    DENSE_RANK() OVER (
        PARTITION BY category 
        ORDER BY annualized_inventory_turnover DESC
    ) AS category_efficiency_rank
FROM turnover_computation
ORDER BY inventory_turns DESC;
