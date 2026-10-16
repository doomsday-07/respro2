-- ==============================================================================
-- Query 03: Multi-Store Gross Margin, Margin Variance & GMROI Analytics
-- Evaluates profitability yield, product pricing power, and GMROI.
-- GMROI Formula: (Gross Margin Dollars) / (Average Inventory Investment at Cost)
-- ==============================================================================

WITH store_product_sales AS (
    SELECT
        tx.store_id,
        st.name AS store_name,
        st.region,
        p.category,
        p.sub_category,
        p.product_id,
        p.product_name,
        p.target_margin_pct,
        SUM(tx.units_sold) AS units_sold,
        SUM(tx.gross_revenue) AS total_revenue,
        SUM(tx.cogs) AS total_cogs,
        SUM(tx.gross_margin) AS total_gross_margin
    FROM fact_sales_transactions tx
    JOIN dim_stores st ON tx.store_id = st.store_id
    JOIN dim_products p ON tx.product_id = p.product_id
    GROUP BY
        tx.store_id, st.name, st.region,
        p.category, p.sub_category, p.product_id,
        p.product_name, p.target_margin_pct
),

store_inventory_cost AS (
    SELECT
        store_id,
        product_id,
        AVG(inventory_value) AS avg_inventory_investment
    FROM fact_daily_inventory
    GROUP BY store_id, product_id
),

combined_profitability AS (
    SELECT
        sps.store_id,
        sps.store_name,
        sps.region,
        sps.category,
        sps.sub_category,
        sps.product_id,
        sps.product_name,
        sps.target_margin_pct,
        sps.units_sold,
        sps.total_revenue,
        sps.total_cogs,
        sps.total_gross_margin,
        COALESCE(sic.avg_inventory_investment, 1.0) AS avg_inventory_investment,
        -- Actual Achieved Gross Margin %
        ROUND(
            CASE 
                WHEN sps.total_revenue > 0 
                THEN (sps.total_gross_margin / sps.total_revenue) * 100.0 
                ELSE 0.0 
            END, 2
        ) AS achieved_margin_pct,
        -- Gross Margin Return on Investment (GMROI)
        ROUND(
            CASE 
                WHEN COALESCE(sic.avg_inventory_investment, 0) > 0 
                THEN sps.total_gross_margin / sic.avg_inventory_investment 
                ELSE 0.0 
            END, 2
        ) AS gmroi_ratio
    FROM store_product_sales sps
    LEFT JOIN store_inventory_cost sic 
        ON sps.store_id = sic.store_id AND sps.product_id = sic.product_id
)

SELECT
    store_name,
    region,
    category,
    product_name,
    units_sold,
    ROUND(total_revenue, 2) AS revenue,
    ROUND(total_gross_margin, 2) AS gross_profit,
    target_margin_pct,
    achieved_margin_pct,
    -- Margin Gap (Achieved vs Target)
    ROUND((achieved_margin_pct - target_margin_pct), 2) AS margin_variance_pts,
    gmroi_ratio,
    -- Quartile ranking within category for profitability yield
    NTILE(4) OVER (
        PARTITION BY category 
        ORDER BY achieved_margin_pct DESC
    ) AS margin_quartile,
    -- GMROI Performance Classification
    CASE
        WHEN gmroi_ratio >= 3.0 THEN 'Elite Capital Yield (Tier 1)'
        WHEN gmroi_ratio >= 1.8 THEN 'Strong Performer (Tier 2)'
        WHEN gmroi_ratio >= 1.0 THEN 'Breakeven Return (Tier 3)'
        ELSE 'Capital Drag (Sub-Optimal)'
    END AS capital_efficiency_tier
FROM combined_profitability
ORDER BY total_gross_margin DESC;
