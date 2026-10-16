-- ==============================================================================
-- Query 06: Executive Multi-Store Performance Scorecard & Composite Ranking
-- Aggregates Revenue, Target Achievement, Gross Margin %, STR, and Stockout Penalty.
-- Produces executive store leaderboard with window ranking and regional benchmarks.
-- ==============================================================================

WITH store_sales_summary AS (
    SELECT
        st.store_id,
        st.name AS store_name,
        st.store_type,
        st.region,
        st.target_monthly_revenue,
        SUM(tx.gross_revenue) AS total_revenue,
        SUM(tx.cogs) AS total_cogs,
        SUM(tx.gross_margin) AS total_gross_margin,
        SUM(tx.units_sold) AS total_units_sold,
        COUNT(DISTINCT tx.transaction_id) AS total_transactions,
        ROUND(AVG(tx.gross_revenue), 2) AS avg_basket_size
    FROM dim_stores st
    LEFT JOIN fact_sales_transactions tx ON st.store_id = tx.store_id
    GROUP BY
        st.store_id, st.name, st.store_type,
        st.region, st.target_monthly_revenue
),

store_inventory_summary AS (
    SELECT
        store_id,
        AVG(inventory_value) AS avg_inventory_value,
        SUM(units_sold) AS inv_units_sold,
        SUM(beginning_inventory + received_units) AS inv_total_exposure,
        SUM(CASE WHEN stockout_flag THEN 1 ELSE 0 END) AS total_stockout_days,
        COUNT(*) AS total_inventory_records
    FROM fact_daily_inventory
    GROUP BY store_id
),

combined_store_kpis AS (
    SELECT
        sss.store_id,
        sss.store_name,
        sss.store_type,
        sss.region,
        sss.target_monthly_revenue,
        sss.total_revenue,
        sss.total_gross_margin,
        sss.total_transactions,
        sss.avg_basket_size,
        -- Gross Margin %
        ROUND(
            CASE 
                WHEN sss.total_revenue > 0 
                THEN (sss.total_gross_margin / sss.total_revenue) * 100.0 
                ELSE 0.0 
            END, 2
        ) AS gross_margin_pct,
        -- Sell-Through Rate %
        ROUND(
            CASE 
                WHEN sis.inv_total_exposure > 0 
                THEN (CAST(sis.inv_units_sold AS FLOAT) / sis.inv_total_exposure) * 100.0 
                ELSE 0.0 
            END, 2
        ) AS sell_through_rate_pct,
        -- Stockout Incident Rate %
        ROUND(
            CASE 
                WHEN sis.total_inventory_records > 0 
                THEN (CAST(sis.total_stockout_days AS FLOAT) / sis.total_inventory_records) * 100.0 
                ELSE 0.0 
            END, 2
        ) AS stockout_rate_pct,
        -- Target Attainment Ratio (6-month annualized basis)
        ROUND(
            (sss.total_revenue / (sss.target_monthly_revenue * 6.0)) * 100.0, 2
        ) AS target_attainment_pct
    FROM store_sales_summary sss
    JOIN store_inventory_summary sis ON sss.store_id = sis.store_id
),

normalized_composite_scores AS (
    SELECT
        store_id,
        store_name,
        store_type,
        region,
        total_revenue,
        gross_margin_pct,
        sell_through_rate_pct,
        stockout_rate_pct,
        target_attainment_pct,
        -- Composite Score Formula (Weighted Index out of 100)
        ROUND(
            (0.35 * (target_attainment_pct / 1.2)) + 
            (0.25 * gross_margin_pct) + 
            (0.25 * (sell_through_rate_pct * 3.5)) - 
            (0.15 * (stockout_rate_pct * 10.0)),
            1
        ) AS executive_composite_score
    FROM combined_store_kpis
)

SELECT
    store_name,
    store_type,
    region,
    ROUND(total_revenue, 2) AS total_revenue,
    target_attainment_pct,
    gross_margin_pct,
    sell_through_rate_pct,
    stockout_rate_pct,
    executive_composite_score,
    -- National Overall Ranking
    RANK() OVER (ORDER BY executive_composite_score DESC) AS national_rank,
    -- Regional Ranking
    DENSE_RANK() OVER (PARTITION BY region ORDER BY executive_composite_score DESC) AS regional_rank,
    -- Regional Average Attainment Benchmark
    ROUND(
        AVG(target_attainment_pct) OVER (PARTITION BY region), 2
    ) AS regional_avg_attainment_pct
FROM normalized_composite_scores
ORDER BY executive_composite_score DESC;
