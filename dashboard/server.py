"""
FastAPI Server for Realtime Sales Performance & Inventory Optimization Dashboard.
Provides REST analytical endpoints, automated report downloads, and WebSocket live POS stream.
"""

import asyncio
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from config import BASE_DIR, EXPORTS_DIR
from analytics.kpi_engine import RetailKpiEngine
from analytics.anomaly_detector import RetailAnomalyDetector
from analytics.forecaster import RetailDemandForecaster
from analytics.inventory_optimizer import InventoryOptimizer
from excel.generator import ExecutiveExcelReportGenerator
from tableau.export_tableau_data import export_tableau_extracts

logger = logging.getLogger("RetailBI.Server")

app = FastAPI(
    title="Realtime Retail BI & Inventory Optimization Dashboard",
    version="2.0.0",
    description="End-to-end retail business intelligence, forecasting, and anomaly detection."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
kpi_engine = RetailKpiEngine()
anomaly_detector = RetailAnomalyDetector()
forecaster = RetailDemandForecaster()
optimizer = InventoryOptimizer()

# Static directory
STATIC_DIR = BASE_DIR / "dashboard" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.api_route("/", methods=["GET", "HEAD"])
def serve_index():
    """Serves the executive web BI dashboard."""
    index_file = STATIC_DIR / "index.html"
    return FileResponse(str(index_file))


@app.get("/api/kpis")
def get_kpis(store_id: Optional[str] = Query(None), category: Optional[str] = Query(None)):
    """Executive KPI scorecard metrics."""
    return kpi_engine.get_executive_summary(store_id=store_id, category=category)


@app.get("/api/trend")
def get_trend(store_id: Optional[str] = Query(None), category: Optional[str] = Query(None)):
    """Daily revenue, COGS, and margin timeseries."""
    return kpi_engine.get_daily_revenue_trend(store_id=store_id, category=category)


@app.get("/api/categories")
def get_categories():
    """Category breakdown of revenue, margins, and sell-through."""
    return kpi_engine.get_category_performance()


@app.get("/api/stores")
def get_stores():
    """Multi-store scorecard leaderboard."""
    return kpi_engine.get_store_leaderboard()


@app.get("/api/forecast")
def get_forecast(store_id: Optional[str] = Query(None), category: Optional[str] = Query(None)):
    """30-day forward demand and revenue forecast with confidence intervals."""
    return forecaster.generate_forecast(store_id=store_id, category=category)


@app.get("/api/anomalies")
def get_anomalies(limit: int = Query(15)):
    """Recent demand surges and inventory anomalies."""
    return anomaly_detector.get_recent_anomalies(limit=limit)


@app.get("/api/optimize")
def get_optimization():
    """Returns dynamic safety stock calculations and the 18% stockout reduction proof."""
    simulation = optimizer.simulate_stockout_reduction()
    recommendations = optimizer.get_top_reorder_recommendations(limit=10)
    return {
        "simulation": simulation,
        "recommendations": recommendations
    }


@app.get("/api/export/excel")
def download_excel():
    """Generates and downloads the executive Excel workbook."""
    gen = ExecutiveExcelReportGenerator()
    excel_path = gen.generate_report()
    return FileResponse(
        str(excel_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Executive_Retail_Sales_Inventory_Report.xlsx"
    )


@app.get("/api/export/tableau")
def trigger_tableau_export():
    """Exports updated CSV extracts for Tableau."""
    paths = export_tableau_extracts()
    return {
        "status": "SUCCESS",
        "message": "Tableau extracts updated successfully in data/exports/",
        "files": {k: str(v.name) for k, v in paths.items()}
    }


@app.websocket("/ws/live-sales")
async def websocket_live_sales(websocket: WebSocket):
    """
    Simulates real-time POS transactional stream across multi-store locations.
    Emits simulated live checkout events and real-time anomaly alerts.
    """
    await websocket.accept()
    logger.info("Client connected to Realtime POS stream WebSocket.")

    stores = ["Manhattan 5th Ave", "Chicago Michigan Ave", "SF Union Square", "Austin Domain", "Dallas Galleria", "Omnichannel Hub"]
    products = [
        ("Ultra HD 4K OLED TV 65\"", "Electronics", 1299.99),
        ("Noise-Cancelling Pro Headphones", "Electronics", 249.99),
        ("Precision Fitness Smartwatch V3", "Electronics", 199.99),
        ("Selvedge Japanese Denim Jeans", "Apparel", 119.99),
        ("Waterproof Thermal Mountain Parka", "Apparel", 259.99),
        ("Artisan Compact Espresso Machine", "Home & Living", 399.99),
        ("Cushioned Carbon-Plate Marathon Runner", "Footwear", 189.99),
        ("Handcrafted Italian Leather Loafers", "Footwear", 229.99),
        ("Automatic Chronograph Sapphire Watch", "Luxury & Accessories", 799.99),
    ]

    try:
        while True:
            # Simulate 1 to 3 items in a basket
            store = random.choice(stores)
            prod_name, cat, price = random.choice(products)
            qty = random.choices([1, 2, 3, 8], weights=[0.70, 0.20, 0.08, 0.02])[0]
            gross = round(price * qty, 2)

            is_surge = (qty >= 5) or (random.random() < 0.05)

            event = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "store": store,
                "product": prod_name,
                "category": cat,
                "units": qty,
                "gross_revenue": gross,
                "channel": random.choice(["In-Store POS", "BOPIS", "Mobile Pay"]),
                "is_surge_anomaly": is_surge,
                "alert": f"🚨 DEMAND SURGE DETECTED: {qty} units of {prod_name} at {store}!" if is_surge else None
            }

            await websocket.send_text(json.dumps(event))
            # Sleep between 1.5 and 3.0 seconds
            await asyncio.sleep(random.uniform(1.5, 3.0))

    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket.")
    except Exception as e:
        logger.warning(f"WebSocket closed: {e}")
