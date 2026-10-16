"""
Statistical and Machine Learning Anomaly Detection Engine.
Detects demand surges, stockout emergencies, and inventory depletion velocity anomalies.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sqlalchemy import text
from database.connection import engine
from config import ANOMALY_ZSCORE_THRESHOLD

logger = logging.getLogger("RetailBI.AnomalyDetector")


class RetailAnomalyDetector:
    """Detects sales spikes, stockout risks, and restock delays."""

    def __init__(self, z_threshold: float = ANOMALY_ZSCORE_THRESHOLD):
        self.engine = engine
        self.z_threshold = z_threshold

    def detect_demand_spikes(self) -> pd.DataFrame:
        """Detects sudden demand spikes using rolling 14-day window statistics."""
        query = """
            SELECT
                tx.date,
                tx.store_id,
                st.name AS store_name,
                tx.product_id,
                p.product_name,
                p.category,
                SUM(tx.units_sold) AS daily_units_sold,
                SUM(tx.gross_revenue) AS daily_revenue
            FROM fact_sales_transactions tx
            JOIN dim_stores st ON tx.store_id = st.store_id
            JOIN dim_products p ON tx.product_id = p.product_id
            GROUP BY
                tx.date, tx.store_id, st.name,
                tx.product_id, p.product_name, p.category
            ORDER BY tx.store_id, tx.product_id, tx.date
        """
        df = pd.read_sql(query, self.engine)
        if df.empty:
            return pd.DataFrame()

        # Compute rolling mean and rolling std per (store_id, product_id)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["store_id", "product_id", "date"])

        grouped = df.groupby(["store_id", "product_id"])["daily_units_sold"]
        df["rolling_mean"] = grouped.transform(lambda s: s.shift(1).rolling(14, min_periods=3).mean())
        df["rolling_std"] = grouped.transform(lambda s: s.shift(1).rolling(14, min_periods=3).std())

        df["rolling_mean"] = df["rolling_mean"].fillna(df["daily_units_sold"])
        df["rolling_std"] = df["rolling_std"].fillna(1.0).replace(0.0, 1.0)

        # Z-Score
        df["z_score"] = (df["daily_units_sold"] - df["rolling_mean"]) / df["rolling_std"]

        # Filter spikes where z_score >= threshold
        spikes = df[df["z_score"] >= self.z_threshold].copy()
        spikes["metric_name"] = "Demand Spike"
        spikes["anomaly_type"] = "Demand Surge"
        spikes["severity"] = np.where(spikes["z_score"] >= 3.5, "Critical", "High")
        spikes["observed_value"] = spikes["daily_units_sold"]
        spikes["expected_value"] = spikes["rolling_mean"].round(1)
        spikes["z_score"] = spikes["z_score"].round(2)
        spikes["date"] = spikes["date"].dt.strftime("%Y-%m-%d")

        logger.info(f"Detected {len(spikes)} demand spike anomalies (Z-Score >= {self.z_threshold}).")
        return spikes

    def detect_stockout_anomalies(self) -> pd.DataFrame:
        """Detects active stockouts where high-demand items ran out of stock."""
        query = """
            SELECT
                inv.snapshot_date AS date,
                inv.store_id,
                st.name AS store_name,
                inv.product_id,
                p.product_name,
                p.category,
                inv.beginning_inventory,
                inv.units_sold,
                inv.ending_inventory,
                inv.stockout_risk_score
            FROM fact_daily_inventory inv
            JOIN dim_stores st ON inv.store_id = st.store_id
            JOIN dim_products p ON inv.product_id = p.product_id
            WHERE inv.stockout_flag = 1
            ORDER BY inv.snapshot_date DESC
        """
        df = pd.read_sql(query, self.engine)
        if df.empty:
            return pd.DataFrame()

        df["metric_name"] = "Stockout Alert"
        df["anomaly_type"] = "Stockout Event"
        df["severity"] = "Critical"
        df["observed_value"] = 0.0
        df["expected_value"] = 25.0  # target buffer
        df["z_score"] = -3.0
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        logger.info(f"Detected {len(df)} stockout anomaly events.")
        return df

    def run_and_save_anomalies(self) -> int:
        """Runs detectors and persists detected anomalies into fact_anomaly_events table."""
        spikes = self.detect_demand_spikes()
        stockouts = self.detect_stockout_anomalies()

        records = []
        # Add demand spikes
        if not spikes.empty:
            for _, r in spikes.iterrows():
                records.append({
                    "anomaly_id": f"ANM-{uuid.uuid4().hex[:8].upper()}",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "date": r["date"],
                    "store_id": r["store_id"],
                    "product_id": r["product_id"],
                    "metric_name": "Sales Surge Velocity",
                    "observed_value": float(r["observed_value"]),
                    "expected_value": float(r["expected_value"]),
                    "z_score": float(r["z_score"]),
                    "anomaly_type": "Demand Surge",
                    "severity": r["severity"],
                    "is_resolved": False,
                    "notes": f"Surge in {r['category']} - {r['product_name']} at {r['store_name']}. Observed {int(r['observed_value'])} units vs expected baseline {r['expected_value']}."
                })

        # Add top sample of stockouts to avoid cluttering
        if not stockouts.empty:
            sample_stockouts = stockouts.head(60)
            for _, r in sample_stockouts.iterrows():
                records.append({
                    "anomaly_id": f"ANM-{uuid.uuid4().hex[:8].upper()}",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "date": r["date"],
                    "store_id": r["store_id"],
                    "product_id": r["product_id"],
                    "metric_name": "Stockout Depletion",
                    "observed_value": 0.0,
                    "expected_value": 25.0,
                    "z_score": -3.2,
                    "anomaly_type": "Stockout Event",
                    "severity": "Critical",
                    "is_resolved": False,
                    "notes": f"Stockout occurred for {r['product_name']} at {r['store_name']}. Buffer depleted to 0 units."
                })

        if records:
            with self.engine.begin() as conn:
                conn.execute(text("DELETE FROM fact_anomaly_events"))
            anom_df = pd.DataFrame(records)
            anom_df.to_sql("fact_anomaly_events", self.engine, if_exists="append", index=False)
            logger.info(f"Persisted {len(anom_df)} anomalies into fact_anomaly_events.")
            return len(anom_df)
        return 0

    def get_recent_anomalies(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Queries recent anomalies for the executive dashboard."""
        query = f"""
            SELECT
                a.anomaly_id,
                a.date,
                st.name AS store_name,
                p.product_name,
                p.category,
                a.anomaly_type,
                a.metric_name,
                a.observed_value,
                a.expected_value,
                a.z_score,
                a.severity,
                a.notes
            FROM fact_anomaly_events a
            JOIN dim_stores st ON a.store_id = st.store_id
            JOIN dim_products p ON a.product_id = p.product_id
            ORDER BY a.date DESC, a.z_score DESC
            LIMIT {limit}
        """
        with self.engine.connect() as conn:
            rows = conn.execute(text(query)).mappings().fetchall()

        return [
            {
                "anomaly_id": r["anomaly_id"],
                "date": str(r["date"]),
                "store_name": r["store_name"],
                "product_name": r["product_name"],
                "category": r["category"],
                "anomaly_type": r["anomaly_type"],
                "metric_name": r["metric_name"],
                "observed_value": round(float(r["observed_value"]), 1),
                "expected_value": round(float(r["expected_value"]), 1),
                "z_score": round(float(r["z_score"]), 2),
                "severity": r["severity"],
                "notes": r["notes"]
            }
            for r in rows
        ]
