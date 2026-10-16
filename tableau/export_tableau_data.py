"""
Tableau Data Extract Generator.
Prepares optimized, denormalized flat data sources and star-schema extracts
ready for Tableau Desktop, Tableau Public, or Tableau Server.
"""

import logging
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from database.connection import engine
from config import EXPORTS_DIR

logger = logging.getLogger("RetailBI.TableauExport")


def export_tableau_extracts(output_dir: Path = EXPORTS_DIR):
    """Exports clean, denormalized CSV extracts designed for Tableau."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Generating Tableau-optimized extracts...")

    # 1. Denormalized Retail Mart (Transactions + Dimensions + Inventory status)
    query_mart = """
        SELECT
            tx.transaction_id,
            tx.timestamp,
            tx.date,
            st.store_id,
            st.name AS store_name,
            st.store_type,
            st.region,
            st.city,
            st.state,
            st.manager_name,
            st.target_monthly_revenue,
            p.product_id,
            p.sku,
            p.product_name,
            p.category,
            p.sub_category,
            p.brand,
            p.supplier_name,
            p.lead_time_days,
            p.unit_cost,
            p.list_price,
            p.target_margin_pct,
            tx.units_sold,
            tx.unit_price,
            tx.gross_revenue,
            tx.cogs,
            tx.gross_margin,
            tx.gross_margin_pct,
            tx.discount_pct,
            tx.payment_method,
            tx.channel
        FROM fact_sales_transactions tx
        JOIN dim_stores st ON tx.store_id = st.store_id
        JOIN dim_products p ON tx.product_id = p.product_id
    """
    df_mart = pd.read_sql(query_mart, engine)
    mart_path = output_dir / "tableau_retail_mart.csv"
    df_mart.to_csv(mart_path, index=False)
    logger.info(f"Exported Tableau Retail Mart: {len(df_mart):,} rows -> {mart_path.name}")

    # 2. Daily KPI Snapshots (Lightweight executive summary)
    query_kpi = """
        SELECT
            kpi.snapshot_date,
            st.store_id,
            st.name AS store_name,
            st.region,
            st.store_type,
            kpi.category,
            kpi.total_revenue,
            kpi.total_cogs,
            kpi.gross_margin,
            kpi.gross_margin_pct,
            kpi.units_sold,
            kpi.average_inventory_units,
            kpi.average_inventory_value,
            kpi.sell_through_rate,
            kpi.inventory_turnover,
            kpi.stockout_count,
            kpi.stockout_rate_pct
        FROM fact_kpi_snapshots kpi
        JOIN dim_stores st ON kpi.store_id = st.store_id
    """
    df_kpi = pd.read_sql(query_kpi, engine)
    kpi_path = output_dir / "tableau_daily_kpis.csv"
    df_kpi.to_csv(kpi_path, index=False)
    logger.info(f"Exported Tableau Daily KPIs: {len(df_kpi):,} rows -> {kpi_path.name}")

    # 3. Anomaly Events Log
    query_anom = """
        SELECT
            a.anomaly_id,
            a.date,
            st.name AS store_name,
            st.region,
            p.category,
            p.product_name,
            a.metric_name,
            a.anomaly_type,
            a.severity,
            a.observed_value,
            a.expected_value,
            a.z_score,
            a.notes
        FROM fact_anomaly_events a
        JOIN dim_stores st ON a.store_id = st.store_id
        JOIN dim_products p ON a.product_id = p.product_id
    """
    df_anom = pd.read_sql(query_anom, engine)
    anom_path = output_dir / "tableau_anomalies.csv"
    df_anom.to_csv(anom_path, index=False)
    logger.info(f"Exported Tableau Anomalies: {len(df_anom):,} rows -> {anom_path.name}")

    # 4. Inventory Health & Stockout Exposure
    query_inv = """
        SELECT
            inv.snapshot_date,
            st.name AS store_name,
            st.region,
            p.category,
            p.product_name,
            p.lead_time_days,
            inv.beginning_inventory,
            inv.received_units,
            inv.units_sold,
            inv.ending_inventory,
            inv.inventory_value,
            inv.safety_stock,
            inv.reorder_point,
            inv.stockout_flag,
            inv.stockout_risk_score,
            inv.sell_through_rate
        FROM fact_daily_inventory inv
        JOIN dim_stores st ON inv.store_id = st.store_id
        JOIN dim_products p ON inv.product_id = p.product_id
    """
    df_inv = pd.read_sql(query_inv, engine)
    inv_path = output_dir / "tableau_inventory_health.csv"
    df_inv.to_csv(inv_path, index=False)
    logger.info(f"Exported Tableau Inventory Health: {len(df_inv):,} rows -> {inv_path.name}")

    logger.info("All Tableau extracts successfully produced in data/exports/.")
    return {
        "mart": mart_path,
        "kpis": kpi_path,
        "anomalies": anom_path,
        "inventory": inv_path
    }


if __name__ == "__main__":
    export_tableau_extracts()
