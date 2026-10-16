"""
Master CLI and Pipeline Orchestrator.
Realtime Sales Performance & Inventory Optimization Dashboard.

Usage:
    python run.py --all           # Run ETL, analytics, anomaly detection, Excel, and Tableau exports
    python run.py --serve         # Launch the Executive Real-Time Web BI Dashboard
    python run.py --etl           # Run automated ETL data extraction and relational loading
    python run.py --excel         # Generate the executive Excel report
    python run.py --tableau       # Export Tableau extracts
    python run.py --test          # Run pytest test suite
"""

import argparse
import logging
import sys
import uvicorn
from config import SERVER_HOST, SERVER_PORT
from etl.pipeline import RetailETLPipeline
from analytics.anomaly_detector import RetailAnomalyDetector
from analytics.inventory_optimizer import InventoryOptimizer
from excel.generator import ExecutiveExcelReportGenerator
from tableau.export_tableau_data import export_tableau_extracts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("RetailBI.MasterCLI")


def run_etl():
    """Runs data extraction, cleaning, and database loading."""
    pipeline = RetailETLPipeline()
    summary = pipeline.run(force_generate=True)
    return summary


def run_analytics_and_anomalies():
    """Executes anomaly detection and inventory optimization."""
    logger.info("Running Statistical Anomaly Detection Engine...")
    detector = RetailAnomalyDetector()
    anom_count = detector.run_and_save_anomalies()

    logger.info("Executing Dynamic Inventory Optimization & Stockout Reduction Simulation...")
    optimizer = InventoryOptimizer()
    sim = optimizer.simulate_stockout_reduction()

    logger.info(f"Anomaly Detection Complete: {anom_count} anomalies logged.")
    logger.info(f"Inventory Optimization Result: {sim['summary_statement']}")
    return {"anomalies": anom_count, "simulation": sim}


def run_excel_export():
    """Generates the advanced executive Excel report."""
    logger.info("Generating Executive Excel Workbook...")
    gen = ExecutiveExcelReportGenerator()
    excel_path = gen.generate_report()
    logger.info(f"Excel report ready at: {excel_path}")
    return excel_path


def run_tableau_export():
    """Exports Tableau CSV and data extracts."""
    logger.info("Exporting Tableau Data Sources...")
    paths = export_tableau_extracts()
    logger.info("Tableau data sources updated successfully.")
    return paths


def run_tests():
    """Runs automated pytest suite."""
    import pytest
    logger.info("Executing test suite...")
    exit_code = pytest.main(["-v", "tests/"])
    if exit_code != 0:
        logger.error(f"Tests failed with exit code: {exit_code}")
        sys.exit(exit_code)
    logger.info("All tests passed successfully.")


def run_serve(port: int = None):
    """Starts the FastAPI web server."""
    bind_port = port or SERVER_PORT
    logger.info(f"Starting Realtime Executive Dashboard on http://{SERVER_HOST}:{bind_port}")
    uvicorn.run("dashboard.server:app", host=SERVER_HOST, port=bind_port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Realtime Sales Performance & Inventory Optimization Dashboard")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: ETL, Analytics, Excel, Tableau")
    parser.add_argument("--etl", action="store_true", help="Run ETL pipeline only")
    parser.add_argument("--analytics", action="store_true", help="Run anomaly detection & optimization only")
    parser.add_argument("--excel", action="store_true", help="Generate Excel report only")
    parser.add_argument("--tableau", action="store_true", help="Export Tableau extracts only")
    parser.add_argument("--test", action="store_true", help="Run pytest suite")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI web server")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="Port to bind web server (default: 8002)")

    args = parser.parse_args()

    # Default to --all if no arguments provided
    if not any([args.all, args.etl, args.analytics, args.excel, args.tableau, args.test, args.serve]):
        args.all = True

    if args.all or args.etl:
        run_etl()

    if args.all or args.analytics:
        run_analytics_and_anomalies()

    if args.all or args.excel:
        run_excel_export()

    if args.all or args.tableau:
        run_tableau_export()

    if args.test:
        run_tests()

    if args.serve:
        run_serve(port=args.port)


if __name__ == "__main__":
    main()
