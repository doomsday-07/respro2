-- ==============================================================================
-- Query 01: Sell-Through Rate (STR) Analysis with Rolling Windows & Tiers
-- Computes weekly and monthly Sell-Through Rate across Stores and Categories.
-- STR Formula: (Total Units Sold) / (Beginning Inventory + Units Received) * 100
-- ==============================================================================

WITH daily_inventory_staged AS (
    SELECT
        inv.snapshot_date,
        inv.store_id,
        st.name AS store_name,
        st.region,
        p.product_id,
        p.product_name,
        p.category,
        inv.beginning_inventory,
        inv.received_units,
        inv.units_sold,
        inv.ending_inventory,
        (inv.beginning_inventory + inv.received_units) AS total_stock_available
    FROM fact_daily_inventory inv
    JOIN dim_stores st ON inv.store_id = st.store_id
    JOIN dim_products p ON inv.product_id = p.product_id
),

rolling_metrics AS (
    SELECT
        snapshot_date,
        store_id,
        store_name,
        region,
        category,
        product_id,
        product_name,
        units_sold,
        total_stock_available,
        ending_inventory,
        -- 7-Day Rolling Units Sold
        SUM(units_sold) OVER (
            PARTITION BY store_id, product_id 
            ORDER BY snapshot_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7d_units_sold,
        -- 7-Day Average Available Stock
        AVG(total_stock_available) OVER (
            PARTITION BY store_id, product_id 
            ORDER BY snapshot_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7d_avg_available,
        -- 30-Day Rolling Units Sold
        SUM(units_sold) OVER (
            PARTITION BY store_id, product_id 
            ORDER BY snapshot_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS rolling_30d_units_sold,
        -- 30-Day Cumulative Beginning Stock + Receipts
        SUM(total_stock_available) OVER (
            PARTITION BY store_id, product_id 
            ORDER BY snapshot_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS rolling_30d_stock_exposure
    FROM daily_inventory_staged
),

calculated_str AS (
    SELECT
        snapshot_date,
        store_id,
        store_name,
        region,
        category,
        product_id,
        product_name,
        units_sold,
        ending_inventory,
        -- Daily Sell-Through Rate
        ROUND(
            CASE 
                WHEN total_stock_available > 0 
                THEN (CAST(units_sold AS FLOAT) / total_stock_available) * 100.0 
                ELSE 0.0 
            END, 2
        ) AS daily_str_pct,
        -- Rolling 7-Day Sell-Through Rate
        ROUND(
            CASE 
                WHEN rolling_7d_avg_available > 0 
                THEN (CAST(rolling_7d_units_sold AS FLOAT) / (rolling_7d_avg_available * 7.0)) * 100.0 
                ELSE 0.0 
            END, 2
        ) AS rolling_7d_str_pct,
        -- Rolling 30-Day STR
        ROUND(
            CASE 
                WHEN rolling_30d_stock_exposure > 0 
                THEN (CAST(rolling_30d_units_sold AS FLOAT) / rolling_30d_stock_exposure) * 100.0 
                ELSE 0.0 
            END, 2
        ) AS rolling_30d_str_pct
    FROM rolling_metrics
)

SELECT
    snapshot_date,
    store_name,
    region,
    category,
    product_name,
    units_sold,
    ending_inventory,
    daily_str_pct,
    rolling_7d_str_pct,
    rolling_30d_str_pct,
    -- Retail Performance Velocity Classification
    CASE
        WHEN rolling_7d_str_pct >= 60.0 THEN 'High Velocity Surge'
        WHEN rolling_7d_str_pct >= 35.0 THEN 'Healthy Optimal'
        WHEN rolling_7d_str_pct >= 15.0 THEN 'Moderate / Baseline'
        ELSE 'Underperforming / Slow Moving'
    END AS velocity_tier,
    -- Store Category Ranking
    RANK() OVER (
        PARTITION BY snapshot_date, category 
        ORDER BY rolling_7d_str_pct DESC
    ) AS category_velocity_rank
FROM calculated_str
ORDER BY snapshot_date DESC, rolling_7d_str_pct DESC;
