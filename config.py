"""
Configuration module for Realtime Sales Performance & Inventory Optimization Dashboard.
Handles database connections, directory paths, anomaly detection thresholds, and optimization params.
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"

for path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, EXPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Database
# Supports PostgreSQL (e.g. postgresql+psycopg2://user:password@localhost:5432/retail_bi)
# Falls back to local SQLite database out of the box with zero external dependencies
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'retail_pulse.db'}"
)

# ETL and Data Generation Parameters
SIMULATION_START_DATE = "2026-01-01"
SIMULATION_END_DATE = "2026-06-30"
HISTORICAL_DAYS = 180
STORES_COUNT = 8
PRODUCTS_COUNT = 45

# Anomaly Detection & Forecasting Parameters
ANOMALY_ZSCORE_THRESHOLD = 2.5
ANOMALY_IQR_MULTIPLIER = 1.5
FORECAST_HORIZON_DAYS = 30
SERVICE_LEVEL_Z = 1.645  # 95% cycle service level
TARGET_STOCKOUT_REDUCTION_PCT = 18.0  # Project target: 18% stockout reduction

# Server Settings
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", 8002))
