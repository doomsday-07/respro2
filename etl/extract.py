"""
Extraction module for retail sales and inventory datasets.
Loads raw JSON and CSV extracts from multi-store retail sources.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
from config import RAW_DATA_DIR

logger = logging.getLogger("RetailBI.Extract")


class RetailDataExtractor:
    """Extracts raw datasets from staging and source files."""

    def __init__(self, raw_dir: Path = RAW_DATA_DIR):
        self.raw_dir = raw_dir

    def extract_stores(self) -> pd.DataFrame:
        path = self.raw_dir / "stores_raw.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing stores raw file: {path}")
        with open(path, "r") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        logger.info(f"Extracted {len(df)} store records from {path.name}")
        return df

    def extract_products(self) -> pd.DataFrame:
        path = self.raw_dir / "products_raw.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing products raw file: {path}")
        with open(path, "r") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        logger.info(f"Extracted {len(df)} product records from {path.name}")
        return df

    def extract_transactions(self) -> pd.DataFrame:
        path = self.raw_dir / "pos_transactions_raw.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing transactions raw file: {path}")
        df = pd.read_csv(path)
        logger.info(f"Extracted {len(df):,} POS transaction records from {path.name}")
        return df

    def extract_inventory(self) -> pd.DataFrame:
        path = self.raw_dir / "inventory_snapshots_raw.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing inventory raw file: {path}")
        df = pd.read_csv(path)
        logger.info(f"Extracted {len(df):,} daily inventory snapshots from {path.name}")
        return df

    def extract_restock(self) -> pd.DataFrame:
        path = self.raw_dir / "restock_orders_raw.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing restock raw file: {path}")
        df = pd.read_csv(path)
        logger.info(f"Extracted {len(df):,} restock orders from {path.name}")
        return df

    def extract_all(self) -> Dict[str, pd.DataFrame]:
        """Extracts all multi-store retail source datasets into memory."""
        logger.info("Initiating full multi-source retail extraction...")
        return {
            "stores": self.extract_stores(),
            "products": self.extract_products(),
            "transactions": self.extract_transactions(),
            "inventory": self.extract_inventory(),
            "restock": self.extract_restock()
        }
