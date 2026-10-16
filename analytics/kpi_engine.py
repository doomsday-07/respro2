"""
Retail KPI computation engine.
Executes analytical SQL queries and produces executive metrics, breakdowns, and trend summaries.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import text
from database.connection import engine

logger = logging.getLogger("RetailBI.KpiEngine")


class RetailKpiEngine:
    """Executes analytical queries to compute retail KPIs."""

    def __init__(self):
        self.engine = engine

    def get_executive_summary(
        self,
        store_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculates executive scorecard metrics across all or filtered stores."""
        filters = []
        params = {}
        if store_id and store_id != "ALL":
            filters.append("tx.store_id = :store_id")
            params["store_id"] = store_id
        if category and category != "ALL":
            filters.append("p.category = :category")
            params["category"] = category

        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

        query_sales = f"""
            SELECT
                COUNT(DISTINCT tx.transaction_id) as total_transactions,
                COALESCE(SUM(tx.gross_revenue), 0) as total_revenue,
                COALESCE(SUM(tx.cogs), 0) as total_cogs,
                COALESCE(SUM(tx.gross_margin), 0) as total_gross_margin,
                COALESCE(SUM(tx.units_sold), 0) as total_units_sold,
                COALESCE(AVG(tx.gross_revenue), 0) as avg_basket_size
            FROM fact_sales_transactions tx
            JOIN dim_products p ON tx.product_id = p.product_id
            {where_clause}
        """

        inv_where = ""
        inv_filters = []
        if store_id and store_id != "ALL":
            inv_filters.append("inv.store_id = :store_id")
        if category and category != "ALL":
            inv_filters.append("p.category = :category")
        if inv_filters:
            inv_where = "WHERE " + " AND ".join(inv_filters)

        query_inv = f"""
            SELECT
                COALESCE(AVG(inv.inventory_value), 0) as avg_inventory_value,
                COALESCE(AVG(inv.ending_inventory), 0) as avg_inventory_units,
                COALESCE(SUM(inv.beginning_inventory + inv.received_units), 0) as total_exposure,
                COALESCE(SUM(inv.units_sold), 0) as inv_units_sold,
                COUNT(CASE WHEN inv.stockout_flag THEN 1 END) as stockout_count,
                COUNT(*) as total_inventory_snapshots
            FROM fact_daily_inventory inv
            JOIN dim_products p ON inv.product_id = p.product_id
            {inv_where}
        """

        with self.engine.connect() as conn:
            sales_row = conn.execute(text(query_sales), params).mappings().fetchone()
            inv_row = conn.execute(text(query_inv), params).mappings().fetchone()

        tot_rev = float(sales_row["total_revenue"])
        tot_cogs = float(sales_row["total_cogs"])
        tot_gm = float(sales_row["total_gross_margin"])
        gm_pct = round((tot_gm / tot_rev * 100), 2) if tot_rev > 0 else 0.0

        inv_exposure = float(inv_row["total_exposure"])
        inv_sold = float(inv_row["inv_units_sold"])
        str_pct = round((inv_sold / inv_exposure * 100), 2) if inv_exposure > 0 else 0.0

        avg_inv_val = float(inv_row["avg_inventory_value"])
        # Annualized Inventory Turnover (COGS / Avg Inventory Value)
        turnover = round((tot_cogs * 2.0) / avg_inv_val, 2) if avg_inv_val > 0 else 0.0

        stockouts = int(inv_row["stockout_count"])
        total_snapshots = int(inv_row["total_inventory_snapshots"])
        stockout_rate = round((stockouts / total_snapshots * 100), 2) if total_snapshots > 0 else 0.0

        return {
            "total_revenue": round(tot_rev, 2),
            "total_cogs": round(tot_cogs, 2),
            "gross_margin": round(tot_gm, 2),
            "gross_margin_pct": gm_pct,
            "units_sold": int(sales_row["total_units_sold"]),
            "total_transactions": int(sales_row["total_transactions"]),
            "avg_basket_size": round(float(sales_row["avg_basket_size"]), 2),
            "sell_through_rate": str_pct,
            "inventory_turnover": turnover,
            "stockout_count": stockouts,
            "stockout_rate_pct": stockout_rate,
            "avg_inventory_value": round(avg_inv_val, 2)
        }

    def get_daily_revenue_trend(
        self,
        store_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns daily revenue, COGS, and margin timeseries."""
        filters = []
        params = {}
        if store_id and store_id != "ALL":
            filters.append("tx.store_id = :store_id")
            params["store_id"] = store_id
        if category and category != "ALL":
            filters.append("p.category = :category")
            params["category"] = category

        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

        query = f"""
            SELECT
                tx.date,
                COALESCE(SUM(tx.gross_revenue), 0) as revenue,
                COALESCE(SUM(tx.cogs), 0) as cogs,
                COALESCE(SUM(tx.gross_margin), 0) as margin,
                COALESCE(SUM(tx.units_sold), 0) as units
            FROM fact_sales_transactions tx
            JOIN dim_products p ON tx.product_id = p.product_id
            {where_clause}
            GROUP BY tx.date
            ORDER BY tx.date ASC
        """
        with self.engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().fetchall()

        return [
            {
                "date": str(r["date"]),
                "revenue": round(float(r["revenue"]), 2),
                "cogs": round(float(r["cogs"]), 2),
                "margin": round(float(r["margin"]), 2),
                "units": int(r["units"])
            }
            for r in rows
        ]

    def get_category_performance(self) -> List[Dict[str, Any]]:
        """Category breakdown of revenue, margin, sell-through rate, and inventory."""
        query = """
            SELECT
                p.category,
                COALESCE(SUM(tx.gross_revenue), 0) as revenue,
                COALESCE(SUM(tx.gross_margin), 0) as margin,
                COALESCE(SUM(tx.units_sold), 0) as units_sold
            FROM dim_products p
            LEFT JOIN fact_sales_transactions tx ON p.product_id = tx.product_id
            GROUP BY p.category
            ORDER BY revenue DESC
        """
        with self.engine.connect() as conn:
            rows = conn.execute(text(query)).mappings().fetchall()

        total_rev = sum(float(r["revenue"]) for r in rows)
        res = []
        for r in rows:
            rev = float(r["revenue"])
            margin = float(r["margin"])
            margin_pct = round((margin / rev * 100), 2) if rev > 0 else 0.0
            share_pct = round((rev / total_rev * 100), 2) if total_rev > 0 else 0.0
            res.append({
                "category": r["category"],
                "revenue": round(rev, 2),
                "margin": round(margin, 2),
                "margin_pct": margin_pct,
                "revenue_share_pct": share_pct,
                "units_sold": int(r["units_sold"])
            })
        return res

    def get_store_leaderboard(self) -> List[Dict[str, Any]]:
        """Multi-store scorecard leaderboard."""
        query = """
            SELECT
                st.store_id,
                st.name,
                st.store_type,
                st.region,
                st.city,
                st.state,
                st.target_monthly_revenue,
                COALESCE(SUM(tx.gross_revenue), 0) as total_revenue,
                COALESCE(SUM(tx.gross_margin), 0) as total_margin,
                COALESCE(SUM(tx.units_sold), 0) as units_sold,
                COUNT(DISTINCT tx.transaction_id) as transactions
            FROM dim_stores st
            LEFT JOIN fact_sales_transactions tx ON st.store_id = tx.store_id
            GROUP BY
                st.store_id, st.name, st.store_type,
                st.region, st.city, st.state, st.target_monthly_revenue
            ORDER BY total_revenue DESC
        """
        with self.engine.connect() as conn:
            rows = conn.execute(text(query)).mappings().fetchall()

        results = []
        for r in rows:
            rev = float(r["total_revenue"])
            margin = float(r["total_margin"])
            gm_pct = round((margin / rev * 100), 2) if rev > 0 else 0.0
            target_6m = float(r["target_monthly_revenue"]) * 6.0
            attainment = round((rev / target_6m * 100), 2) if target_6m > 0 else 0.0

            results.append({
                "store_id": r["store_id"],
                "name": r["name"],
                "store_type": r["store_type"],
                "region": r["region"],
                "city": f"{r['city']}, {r['state']}",
                "total_revenue": round(rev, 2),
                "gross_margin": round(margin, 2),
                "gross_margin_pct": gm_pct,
                "units_sold": int(r["units_sold"]),
                "transactions": int(r["transactions"]),
                "target_attainment_pct": attainment
            })
        return results
