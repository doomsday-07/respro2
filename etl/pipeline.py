"""
Automated end-to-end retail ETL pipeline orchestrator.
Manages extraction, cleaning, normalization, validation, and relational database loading.
"""

import logging
import time
from typing import Dict, Any
from etl.generator import generate_raw_retail_datasets
from etl.extract import RetailDataExtractor
from etl.transform import RetailDataTransformer
from etl.load import RetailDataLoader
from config import RAW_DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("RetailBI.ETLPipeline")


class RetailETLPipeline:
    """End-to-end automated retail ETL pipeline."""

    def __init__(self):
        self.extractor = RetailDataExtractor()
        self.transformer = RetailDataTransformer()
        self.loader = RetailDataLoader()

    def run(self, force_generate: bool = False) -> Dict[str, Any]:
        """Executes full automated ETL process."""
        start_time = time.time()
        logger.info("=" * 70)
        logger.info("STARTING AUTOMATED RETAIL BI & INVENTORY ETL PIPELINE")
        logger.info("=" * 70)

        # Step 0: Check raw data
        raw_files = [
            RAW_DATA_DIR / "stores_raw.json",
            RAW_DATA_DIR / "products_raw.json",
            RAW_DATA_DIR / "pos_transactions_raw.csv",
            RAW_DATA_DIR / "inventory_snapshots_raw.csv",
            RAW_DATA_DIR / "restock_orders_raw.csv"
        ]
        if force_generate or not all(f.exists() for f in raw_files):
            logger.info("Raw data missing or force regeneration requested. Generating synthetic datasets...")
            generate_raw_retail_datasets()

        # Step 1: Extraction
        extract_start = time.time()
        raw_datasets = self.extractor.extract_all()
        extract_time = round(time.time() - extract_start, 2)
        logger.info(f"Extraction completed in {extract_time}s.")

        # Step 2: Transformation & Cleaning
        transform_start = time.time()
        clean_datasets = self.transformer.transform_all(raw_datasets)
        transform_time = round(time.time() - transform_start, 2)
        logger.info(f"Transformation completed in {transform_time}s.")

        # Step 3: Loading into Normalized Relational DB
        load_start = time.time()
        self.loader.load_all(clean_datasets, clear_existing=True)
        load_time = round(time.time() - load_start, 2)
        logger.info(f"Loading completed in {load_time}s.")

        # Step 4: Run Statistical Anomaly Detection & Persistence
        try:
            from analytics.anomaly_detector import RetailAnomalyDetector
            detector = RetailAnomalyDetector()
            anom_count = detector.run_and_save_anomalies()
            logger.info(f"Statistical Anomaly Detection automatically logged {anom_count} anomalies.")
        except Exception as e:
            logger.warning(f"Could not auto-run anomaly detection during ETL: {e}")

        # Step 5: Quality & Validation Checks
        validation_report = self._validate_integrity(clean_datasets)

        total_duration = round(time.time() - start_time, 2)
        logger.info("=" * 70)
        logger.info(f"ETL PIPELINE FINISHED SUCCESSFULLY IN {total_duration}s")
        logger.info("=" * 70)

        return {
            "status": "SUCCESS",
            "duration_seconds": total_duration,
            "extract_time": extract_time,
            "transform_time": transform_time,
            "load_time": load_time,
            "records_processed": {
                "stores": len(clean_datasets["stores"]),
                "products": len(clean_datasets["products"]),
                "transactions": len(clean_datasets["transactions"]),
                "inventory_snapshots": len(clean_datasets["inventory"]),
                "restock_orders": len(clean_datasets["restock"]),
                "kpi_snapshots": len(clean_datasets["kpis"]),
            },
            "validation": validation_report
        }

    def _validate_integrity(self, datasets: Dict[str, Any]) -> Dict[str, Any]:
        """Validates primary/foreign key integrity and data bounds."""
        stores_ids = set(datasets["stores"]["store_id"])
        prod_ids = set(datasets["products"]["product_id"])

        tx_stores = set(datasets["transactions"]["store_id"])
        tx_prods = set(datasets["transactions"]["product_id"])

        orphan_stores = tx_stores - stores_ids
        orphan_prods = tx_prods - prod_ids

        total_rev = datasets["transactions"]["gross_revenue"].sum()
        total_cogs = datasets["transactions"]["cogs"].sum()
        avg_margin_pct = ((total_rev - total_cogs) / total_rev * 100) if total_rev > 0 else 0

        stockouts = datasets["inventory"]["stockout_flag"].sum()
        total_inv_rows = len(datasets["inventory"])
        stockout_pct = round((stockouts / total_inv_rows) * 100, 2) if total_inv_rows > 0 else 0

        valid = len(orphan_stores) == 0 and len(orphan_prods) == 0

        report = {
            "referential_integrity_valid": valid,
            "orphan_store_count": len(orphan_stores),
            "orphan_product_count": len(orphan_prods),
            "total_gross_revenue": round(total_rev, 2),
            "total_cogs": round(total_cogs, 2),
            "overall_gross_margin_pct": round(avg_margin_pct, 2),
            "total_stockout_events": int(stockouts),
            "stockout_percentage": stockout_pct
        }
        logger.info(f"Integrity Check: Valid={valid}, Revenue=${total_rev:,.2f}, GM%={avg_margin_pct:.1f}%, Stockout%={stockout_pct}%")
        return report


if __name__ == "__main__":
    pipeline = RetailETLPipeline()
    summary = pipeline.run(force_generate=True)
    print(summary)
