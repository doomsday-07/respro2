"""
Database loader module for retail data warehouse and operational store.
Executes high-throughput batch insertions into normalized tables and data marts.
"""

import logging
from typing import Dict
import pandas as pd
from sqlalchemy import text
from database.connection import engine, init_db
from config import PROCESSED_DATA_DIR

logger = logging.getLogger("RetailBI.Load")


class RetailDataLoader:
    """Loads transformed DataFrames into PostgreSQL / SQLite relational tables."""

    def __init__(self):
        self.engine = engine

    def load_table(self, df: pd.DataFrame, table_name: str, if_exists: str = "append", chunksize: int = 5000):
        """Loads a DataFrame into a SQL table using chunked inserts."""
        if df.empty:
            logger.warning(f"DataFrame for {table_name} is empty. Skipping load.")
            return

        logger.info(f"Loading {len(df):,} records into {table_name}...")
        df.to_sql(
            table_name,
            con=self.engine,
            if_exists=if_exists,
            index=False,
            chunksize=chunksize,
            method="multi"
        )
        logger.info(f"Successfully loaded {table_name}.")

    def save_processed_cache(self, datasets: Dict[str, pd.DataFrame]):
        """Persists processed datasets into data/processed/ for fast local access."""
        logger.info("Persisting processed data snapshots to disk...")
        for name, df in datasets.items():
            cache_path = PROCESSED_DATA_DIR / f"{name}_processed.csv"
            df.to_csv(cache_path, index=False)
        logger.info(f"Saved {len(datasets)} processed datasets to {PROCESSED_DATA_DIR}")

    def load_all(self, datasets: Dict[str, pd.DataFrame], clear_existing: bool = True):
        """Initializes database schema and loads all dimensional & fact tables."""
        logger.info("Initializing relational database schema...")
        init_db()

        if clear_existing:
            logger.info("Clearing existing records in reverse dependency order...")
            with self.engine.begin() as conn:
                for table in [
                    "fact_anomaly_events",
                    "fact_kpi_snapshots",
                    "fact_restock_orders",
                    "fact_daily_inventory",
                    "fact_sales_transactions",
                    "dim_products",
                    "dim_stores"
                ]:
                    try:
                        conn.execute(text(f"DELETE FROM {table}"))
                    except Exception as e:
                        logger.warning(f"Could not truncate {table} (table may be newly created): {e}")

        # Dimensional tables first
        self.load_table(datasets["stores"], "dim_stores", if_exists="append")
        self.load_table(datasets["products"], "dim_products", if_exists="append")

        # Fact tables
        self.load_table(datasets["transactions"], "fact_sales_transactions", if_exists="append", chunksize=5000)
        self.load_table(datasets["inventory"], "fact_daily_inventory", if_exists="append", chunksize=5000)
        self.load_table(datasets["restock"], "fact_restock_orders", if_exists="append", chunksize=2000)
        self.load_table(datasets["kpis"], "fact_kpi_snapshots", if_exists="append", chunksize=5000)

        # Cache processed data
        self.save_processed_cache(datasets)
        logger.info("Full relational warehouse load completed successfully.")
