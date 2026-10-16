-- ==============================================================================
-- Query 05: Statistical Anomaly Detection for Demand Surges (Z-Score & Rolling Stats)
-- Computes dynamic rolling baselines to detect flash sales and demand spikes.
-- Z-Score Formula: (Daily Volume - Rolling 14d Mean) / (Rolling 14d StdDev)
-- ==============================================================================

WITH daily_product_store_sales AS (
    SELECT
        tx.date,
        tx.store_id,
        st.name AS store_name,
        p.product_id,
        p.product_name,
        p.category,
        SUM(tx.units_sold) AS daily_units_sold,
        SUM(tx.gross_revenue) AS daily_revenue
    FROM fact_sales_transactions tx
    JOIN dim_stores st ON tx.store_id = st.store_id
    JOIN dim_products p ON tx.product_id = p.product_id
    GROUP BY
        tx.date, tx.store_id, st.name,
        p.product_id, p.product_name, p.category
),

rolling_sales_statistics AS (
    SELECT
        date,
        store_id,
        store_name,
        product_id,
        product_name,
        category,
        daily_units_sold,
        daily_revenue,
        -- 14-Day Rolling Average Units Sold
        AVG(CAST(daily_units_sold AS FLOAT)) OVER (
            PARTITION BY store_id, product_id 
            ORDER BY date 
            ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
        ) AS rolling_14d_mean,
        -- Rolling 14-day sum of squares for sample variance calculation
        AVG(CAST(daily_units_sold * daily_units_sold AS FLOAT)) OVER (
            PARTITION BY store_id, product_id 
            ORDER BY date 
            ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
        ) AS rolling_14d_mean_sq
    FROM daily_product_store_sales
),

variance_and_zscore AS (
    SELECT
        date,
        store_name,
        product_name,
        category,
        daily_units_sold,
        daily_revenue,
        ROUND(COALESCE(rolling_14d_mean, 1.0), 2) AS baseline_demand,
        -- Rolling Standard Deviation = SQRT(E[X^2] - (E[X])^2)
        ROUND(
            CASE 
                WHEN (rolling_14d_mean_sq - (rolling_14d_mean * rolling_14d_mean)) > 0.05
                THEN SQRT(rolling_14d_mean_sq - (rolling_14d_mean * rolling_14d_mean))
                ELSE 1.0
            END, 2
        ) AS rolling_14d_stdev
    FROM rolling_sales_statistics
),

scored_anomalies AS (
    SELECT
        date,
        store_name,
        product_name,
        category,
        daily_units_sold,
        baseline_demand,
        rolling_14d_stdev,
        daily_revenue,
        -- Dynamic Z-Score
        ROUND(
            (daily_units_sold - baseline_demand) / NULLIF(rolling_14d_stdev, 0),
            2
        ) AS demand_z_score,
        -- Demand Surge Multiplier
        ROUND(
            daily_units_sold / NULLIF(baseline_demand, 0),
            2
        ) AS surge_multiplier
    FROM variance_and_zscore
)

SELECT
    date,
    store_name,
    category,
    product_name,
    daily_units_sold,
    baseline_demand,
    surge_multiplier,
    demand_z_score,
    ROUND(daily_revenue, 2) AS daily_revenue,
    -- Anomaly Severity Classification
    CASE
        WHEN demand_z_score >= 3.5 THEN 'CRITICAL SPIKE (Severe Surge)'
        WHEN demand_z_score >= 2.5 THEN 'HIGH SPIKE (Unusual Demand Surge)'
        WHEN demand_z_score <= -2.0 THEN 'SUDDEN COLLAPSE (Potential Stockout / Choke)'
        ELSE 'NORMAL VARIANCE'
    END AS anomaly_classification
FROM scored_anomalies
WHERE demand_z_score >= 2.5 OR demand_z_score <= -2.0
ORDER BY demand_z_score DESC;
