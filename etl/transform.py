"""
Transformation and cleaning module for retail datasets.
Performs data cleansing, validation, normalization, and KPI derivations.
"""

import logging
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger("RetailBI.Transform")


class RetailDataTransformer:
    """Cleans, normalizes, and enriches retail data."""

    def clean_stores(self, df: pd.DataFrame) -> pd.DataFrame:
        clean_df = df.copy()
        clean_df.drop_duplicates(subset=["store_id"], inplace=True)
        clean_df["square_feet"] = clean_df["square_feet"].fillna(15000).astype(int)
        clean_df["target_monthly_revenue"] = clean_df["target_monthly_revenue"].astype(float).round(2)
        if "is_active" in clean_df.columns:
            clean_df["is_active"] = clean_df["is_active"].fillna(True).astype(bool)
        else:
            clean_df["is_active"] = True
        logger.info(f"Cleaned stores: {len(clean_df)} valid records.")
        return clean_df

    def clean_products(self, df: pd.DataFrame) -> pd.DataFrame:
        clean_df = df.copy()
        clean_df.drop_duplicates(subset=["product_id"], inplace=True)
        clean_df.drop_duplicates(subset=["sku"], inplace=True)
        clean_df["unit_cost"] = clean_df["unit_cost"].astype(float).clip(lower=0.01).round(2)
        clean_df["list_price"] = clean_df["list_price"].astype(float).clip(lower=0.01).round(2)
        clean_df["target_margin_pct"] = (
            ((clean_df["list_price"] - clean_df["unit_cost"]) / clean_df["list_price"]) * 100
        ).round(2)
        clean_df["lead_time_days"] = clean_df["lead_time_days"].fillna(7).astype(int)
        clean_df["reorder_quantity"] = clean_df["reorder_quantity"].fillna(50).astype(int)
        logger.info(f"Cleaned products: {len(clean_df)} valid records.")
        return clean_df

    def clean_transactions(self, df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
        clean_df = df.copy()
        clean_df.drop_duplicates(subset=["transaction_id"], inplace=True)

        # Enforce positive unit sales
        clean_df = clean_df[clean_df["units_sold"] > 0].copy()

        # Parse timestamps and dates
        clean_df["timestamp"] = pd.to_datetime(clean_df["timestamp"])
        clean_df["date"] = pd.to_datetime(clean_df["date"]).dt.date

        # Recalculate and guarantee mathematical accuracy
        clean_df["discount_pct"] = clean_df["discount_pct"].fillna(0.0).clip(lower=0.0, upper=1.0)
        clean_df["units_sold"] = clean_df["units_sold"].astype(int)
        clean_df["unit_price"] = clean_df["unit_price"].astype(float).round(2)
        clean_df["unit_cost"] = clean_df["unit_cost"].astype(float).round(2)

        clean_df["gross_revenue"] = (clean_df["units_sold"] * clean_df["unit_price"]).round(2)
        clean_df["cogs"] = (clean_df["units_sold"] * clean_df["unit_cost"]).round(2)
        clean_df["gross_margin"] = (clean_df["gross_revenue"] - clean_df["cogs"]).round(2)

        # Avoid zero-division on margin pct
        clean_df["gross_margin_pct"] = np.where(
            clean_df["gross_revenue"] > 0,
            ((clean_df["gross_margin"] / clean_df["gross_revenue"]) * 100).round(2),
            0.0
        )

        clean_df["payment_method"] = clean_df["payment_method"].fillna("Credit Card")
        clean_df["channel"] = clean_df["channel"].fillna("In-Store")

        logger.info(f"Cleaned transactions: {len(clean_df):,} valid rows. Total Gross Revenue: ${clean_df['gross_revenue'].sum():,.2f}")
        return clean_df

    def clean_inventory(self, df: pd.DataFrame) -> pd.DataFrame:
        clean_df = df.copy()
        clean_df.drop_duplicates(subset=["store_id", "product_id", "snapshot_date"], inplace=True)

        clean_df["snapshot_date"] = pd.to_datetime(clean_df["snapshot_date"]).dt.date
        clean_df["beginning_inventory"] = clean_df["beginning_inventory"].fillna(0).astype(int).clip(lower=0)
        clean_df["received_units"] = clean_df["received_units"].fillna(0).astype(int).clip(lower=0)
        clean_df["units_sold"] = clean_df["units_sold"].fillna(0).astype(int).clip(lower=0)

        # Mathematical consistency for ending inventory
        clean_df["ending_inventory"] = (
            clean_df["beginning_inventory"] + clean_df["received_units"] - clean_df["units_sold"]
        ).clip(lower=0)

        clean_df["inventory_value"] = clean_df["inventory_value"].astype(float).round(2)
        clean_df["safety_stock"] = clean_df["safety_stock"].fillna(20).astype(int)
        clean_df["reorder_point"] = clean_df["reorder_point"].fillna(40).astype(int)
        clean_df["stockout_flag"] = clean_df["ending_inventory"] == 0

        # Sell-through rate
        available = clean_df["beginning_inventory"] + clean_df["received_units"]
        clean_df["sell_through_rate"] = np.where(
            available > 0,
            ((clean_df["units_sold"] / available) * 100).round(2),
            0.0
        )

        clean_df["stockout_risk_score"] = clean_df["stockout_risk_score"].fillna(0.0).astype(float).round(2)

        logger.info(f"Cleaned inventory: {len(clean_df):,} snapshots. Stockout instances: {clean_df['stockout_flag'].sum():,}")
        return clean_df

    def clean_restock(self, df: pd.DataFrame) -> pd.DataFrame:
        clean_df = df.copy()
        clean_df.drop_duplicates(subset=["order_id"], inplace=True)
        clean_df["order_date"] = pd.to_datetime(clean_df["order_date"]).dt.date
        clean_df["expected_delivery_date"] = pd.to_datetime(clean_df["expected_delivery_date"]).dt.date
        if "actual_delivery_date" in clean_df.columns:
            clean_df["actual_delivery_date"] = pd.to_datetime(clean_df["actual_delivery_date"]).dt.date
        clean_df["order_quantity"] = clean_df["order_quantity"].astype(int)
        clean_df["unit_cost"] = clean_df["unit_cost"].astype(float).round(2)
        clean_df["total_cost"] = (clean_df["order_quantity"] * clean_df["unit_cost"]).round(2)
        clean_df["status"] = clean_df["status"].fillna("Delivered")
        logger.info(f"Cleaned restock orders: {len(clean_df):,} records.")
        return clean_df

    def compute_daily_kpis(
        self,
        tx_df: pd.DataFrame,
        inv_df: pd.DataFrame,
        prod_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Computes daily aggregated retail KPIs by (snapshot_date, store_id, category)."""
        logger.info("Computing pre-aggregated daily retail KPIs...")

        # Join transactions with products for category
        tx_merged = tx_df.merge(
            prod_df[["product_id", "category"]],
            on="product_id",
            how="left"
        )

        # Aggregate sales by (date, store_id, category)
        sales_agg = tx_merged.groupby(["date", "store_id", "category"]).agg(
            total_revenue=("gross_revenue", "sum"),
            total_cogs=("cogs", "sum"),
            gross_margin=("gross_margin", "sum"),
            units_sold=("units_sold", "sum")
        ).reset_index().rename(columns={"date": "snapshot_date"})

        # Join inventory with products for category
        inv_merged = inv_df.merge(
            prod_df[["product_id", "category"]],
            on="product_id",
            how="left"
        )

        inv_agg = inv_merged.groupby(["snapshot_date", "store_id", "category"]).agg(
            average_inventory_units=("ending_inventory", "mean"),
            average_inventory_value=("inventory_value", "mean"),
            stockout_count=("stockout_flag", "sum"),
            total_sku_count=("product_id", "count"),
            total_beginning=("beginning_inventory", "sum"),
            total_received=("received_units", "sum"),
            total_inv_sold=("units_sold", "sum")
        ).reset_index()

        kpi_df = pd.merge(
            inv_agg,
            sales_agg,
            on=["snapshot_date", "store_id", "category"],
            how="left"
        )

        # Fill NaNs for days/categories without sales
        kpi_df["total_revenue"] = kpi_df["total_revenue"].fillna(0.0).round(2)
        kpi_df["total_cogs"] = kpi_df["total_cogs"].fillna(0.0).round(2)
        kpi_df["gross_margin"] = kpi_df["gross_margin"].fillna(0.0).round(2)
        kpi_df["units_sold"] = kpi_df["units_sold"].fillna(0).astype(int)

        kpi_df["gross_margin_pct"] = np.where(
            kpi_df["total_revenue"] > 0,
            ((kpi_df["gross_margin"] / kpi_df["total_revenue"]) * 100).round(2),
            0.0
        )

        denom = kpi_df["total_beginning"] + kpi_df["total_received"]
        kpi_df["sell_through_rate"] = np.where(
            denom > 0,
            ((kpi_df["total_inv_sold"] / denom) * 100).round(2),
            0.0
        )

        # Annualized Inventory Turnover: (COGS * 365) / Average Inventory Value
        # For daily snapshot, compute ratio on annualized basis
        kpi_df["inventory_turnover"] = np.where(
            kpi_df["average_inventory_value"] > 0,
            ((kpi_df["total_cogs"] * 365) / kpi_df["average_inventory_value"]).round(2),
            0.0
        )

        kpi_df["stockout_rate_pct"] = np.where(
            kpi_df["total_sku_count"] > 0,
            ((kpi_df["stockout_count"] / kpi_df["total_sku_count"]) * 100).round(2),
            0.0
        )

        kpi_df["average_inventory_units"] = kpi_df["average_inventory_units"].round(2)
        kpi_df["average_inventory_value"] = kpi_df["average_inventory_value"].round(2)

        # Keep relevant columns matching KpiDailySnapshot model
        cols = [
            "snapshot_date", "store_id", "category", "total_revenue", "total_cogs",
            "gross_margin", "gross_margin_pct", "units_sold", "average_inventory_units",
            "average_inventory_value", "sell_through_rate", "inventory_turnover",
            "stockout_count", "stockout_rate_pct"
        ]
        res_df = kpi_df[cols].copy()
        logger.info(f"Generated {len(res_df):,} daily KPI snapshot records.")
        return res_df

    def transform_all(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Runs complete transformation pipeline across all datasets."""
        stores = self.clean_stores(raw_data["stores"])
        products = self.clean_products(raw_data["products"])
        tx = self.clean_transactions(raw_data["transactions"], products)
        inv = self.clean_inventory(raw_data["inventory"])
        restock = self.clean_restock(raw_data["restock"])
        kpis = self.compute_daily_kpis(tx, inv, products)

        return {
            "stores": stores,
            "products": products,
            "transactions": tx,
            "inventory": inv,
            "restock": restock,
            "kpis": kpis
        }
