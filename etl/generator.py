"""
Multi-Store Retail Dataset Generator.
Synthesizes multi-store retail sales, inventory movements, restock orders,
and real-world demand spikes / stockout anomalies.
"""

import json
import logging
import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from config import (
    RAW_DATA_DIR, SIMULATION_START_DATE, SIMULATION_END_DATE,
    STORES_COUNT, PRODUCTS_COUNT
)

logger = logging.getLogger("RetailBI.DataGenerator")
logging.basicConfig(level=logging.INFO)

# Deterministic seed for reproducibility
random.seed(42)
np.random.seed(42)

STORES_DEF = [
    {"store_id": "STR-001", "name": "Manhattan 5th Ave Flagship", "store_type": "Flagship", "region": "East", "city": "New York", "state": "NY", "square_feet": 28000, "manager_name": "Eleanor Vance", "target_monthly_revenue": 480000.0},
    {"store_id": "STR-002", "name": "Chicago Michigan Ave Center", "store_type": "Downtown", "region": "Midwest", "city": "Chicago", "state": "IL", "square_feet": 20000, "manager_name": "Marcus Kane", "target_monthly_revenue": 340000.0},
    {"store_id": "STR-003", "name": "SF Union Square Tech Hub", "store_type": "Flagship", "region": "West", "city": "San Francisco", "state": "CA", "square_feet": 24000, "manager_name": "Aria Patel", "target_monthly_revenue": 420000.0},
    {"store_id": "STR-004", "name": "Austin Domain Town Center", "store_type": "Suburban", "region": "South", "city": "Austin", "state": "TX", "square_feet": 16000, "manager_name": "Tyler Brooks", "target_monthly_revenue": 260000.0},
    {"store_id": "STR-005", "name": "Dallas Galleria Megastore", "store_type": "Mall", "region": "South", "city": "Dallas", "state": "TX", "square_feet": 22000, "manager_name": "Samantha Cruz", "target_monthly_revenue": 310000.0},
    {"store_id": "STR-006", "name": "Seattle Pike Place Boutique", "store_type": "Express", "region": "West", "city": "Seattle", "state": "WA", "square_feet": 12000, "manager_name": "David Sterling", "target_monthly_revenue": 210000.0},
    {"store_id": "STR-007", "name": "Miami Brickell Promenade", "store_type": "Mall", "region": "East", "city": "Miami", "state": "FL", "square_feet": 18000, "manager_name": "Sofia Reyes", "target_monthly_revenue": 290000.0},
    {"store_id": "STR-008", "name": "Omnichannel Hub & Express", "store_type": "Distribution Hub", "region": "Midwest", "city": "Columbus", "state": "OH", "square_feet": 45000, "manager_name": "Jordan Lee", "target_monthly_revenue": 550000.0},
]

CATEGORIES_DEF = {
    "Electronics": [
        ("Ultra HD 4K OLED TV 65\"", "Televisions", "LumixVision", 750.0, 1299.99, 10, 30),
        ("Noise-Cancelling Pro Headphones", "Audio", "SonicWave", 120.0, 249.99, 7, 50),
        ("Precision Fitness Smartwatch V3", "Wearables", "PulseTrack", 95.0, 199.99, 7, 60),
        ("NextGen Tablet Pro 11-inch", "Computers", "NovaTech", 320.0, 599.99, 10, 40),
        ("Ergonomic Wireless Mechanical Keyboard", "Accessories", "KeyCraft", 45.0, 99.99, 5, 80),
        ("True Wireless ANC Earbuds", "Audio", "SonicWave", 55.0, 129.99, 5, 100),
        ("Smart Home Mesh Wi-Fi 6 Router", "Networking", "OmniNet", 80.0, 179.99, 8, 45),
        ("4K Ultra-Wide Studio Monitor 34\"", "Displays", "LumixVision", 280.0, 499.99, 12, 35),
        ("Wireless Fast Charging Stand Duo", "Accessories", "NovaTech", 20.0, 49.99, 5, 90),
    ],
    "Apparel": [
        ("Tailored Stretch Cotton Blazer", "Formalwear", "Avenue & Co", 65.0, 169.99, 12, 40),
        ("Selvedge Japanese Denim Jeans", "Bottoms", "IndigoThread", 40.0, 119.99, 10, 60),
        ("Performance Breathable Polo Shirt", "Tops", "Avenue & Co", 22.0, 59.99, 7, 80),
        ("Waterproof Thermal Mountain Parka", "Outerwear", "NordicPeak", 110.0, 259.99, 14, 35),
        ("100% Merino Wool Crewneck Sweater", "Knitwear", "NordicPeak", 48.0, 129.99, 12, 45),
        ("French Terry Oversized Hoodie", "Casualwear", "UrbanForge", 30.0, 79.99, 7, 75),
        ("Moisture-Wicking Athletic Joggers", "Activewear", "UrbanForge", 26.0, 69.99, 7, 70),
        ("Classic Fit Egyptian Cotton Oxford", "Tops", "Avenue & Co", 28.0, 74.99, 8, 65),
        ("Lightweight Packable Windbreaker", "Outerwear", "NordicPeak", 38.0, 89.99, 10, 50),
    ],
    "Home & Living": [
        ("Artisan Compact Espresso Machine", "Kitchenware", "BaristaLab", 180.0, 399.99, 14, 25),
        ("HEPA Smart Air Purifier Pro", "Appliances", "AeroPure", 90.0, 199.99, 10, 40),
        ("Pre-Seasoned Cast Iron Dutch Oven", "Cookware", "HeritageIron", 42.0, 99.99, 12, 35),
        ("Hand-Poured Soy Aromatherapy Candle", "Decor", "LuminaHome", 12.0, 32.00, 5, 120),
        ("Egyptian Long-Staple Sateen Sheet Set", "Bedding", "LuxeLinens", 58.0, 149.99, 10, 50),
        ("Motorized Standing Desk Converter", "Furniture", "ErgoCraft", 140.0, 299.99, 15, 30),
        ("Stainless Steel Chef Knife 8-inch", "Cutlery", "HeritageIron", 35.0, 89.99, 8, 60),
        ("Minimalist Ceramic Dinnerware Set 16pc", "Dining", "LuminaHome", 50.0, 129.99, 14, 40),
        ("Cordless Stick Vacuum Ultra", "Appliances", "AeroPure", 115.0, 249.99, 12, 35),
    ],
    "Footwear": [
        ("Cushioned Carbon-Plate Marathon Runner", "Running", "VeloceRun", 85.0, 189.99, 10, 45),
        ("Handcrafted Italian Leather Loafers", "Formal", "ModenaCraft", 95.0, 229.99, 14, 30),
        ("All-Weather Waterproof Trail Boot", "Outdoor", "SummitPath", 70.0, 159.99, 12, 40),
        ("Minimalist Daily Canvas Sneaker", "Casual", "VeloceRun", 28.0, 69.99, 7, 90),
        ("Slip-On Memory Foam Recovery Slide", "Sandals", "VeloceRun", 16.0, 39.99, 5, 110),
        ("Goodyear Welted Suede Chelsea Boot", "Boots", "ModenaCraft", 110.0, 249.99, 15, 30),
        ("Court Classic Tennis Sneaker", "Sport", "UrbanForge", 36.0, 89.99, 8, 70),
        ("High-Traction Hiking Shoe", "Outdoor", "SummitPath", 52.0, 129.99, 10, 50),
        ("Water-Resistant Winter Snow Boot", "Winter", "SummitPath", 68.0, 149.99, 14, 35),
    ],
    "Luxury & Accessories": [
        ("Automatic Chronograph Sapphire Watch", "Timepieces", "HorologyGeneve", 350.0, 799.99, 20, 20),
        ("Full-Grain Italian Leather Bifold Wallet", "Leather Goods", "ModenaCraft", 32.0, 89.99, 8, 60),
        ("Polarized Aviator Titanium Sunglasses", "Eyewear", "AeroShield", 60.0, 159.99, 7, 50),
        ("Full-Grain Leather Weekender Duffle", "Travel", "ModenaCraft", 130.0, 299.99, 15, 25),
        ("Sterling Silver Modern Cufflinks", "Jewelry", "HorologyGeneve", 40.0, 110.00, 10, 40),
        ("Thermal Insulated Stainless Steel Tumbler", "Drinkware", "LuminaHome", 14.0, 34.99, 5, 100),
        ("RFID-Blocking Cardholder Slim", "Accessories", "Avenue & Co", 15.0, 39.99, 6, 80),
        ("Pure Cashmere Fringed Scarf", "Winter", "NordicPeak", 50.0, 139.99, 12, 35),
        ("Handcrafted Brass Desk Clock", "Timepieces", "HorologyGeneve", 45.0, 119.99, 10, 30),
    ]
}


def generate_raw_retail_datasets():
    """Generates normalized raw datasets and writes them to data/raw/."""
    logger.info("Generating realistic multi-store retail datasets...")

    # 1. Stores
    stores_df = pd.DataFrame(STORES_DEF)
    stores_raw_path = RAW_DATA_DIR / "stores_raw.json"
    with open(stores_raw_path, "w") as f:
        json.dump(STORES_DEF, f, indent=2)

    # 2. Products
    products = []
    prod_counter = 1
    for cat_name, items in CATEGORIES_DEF.items():
        for name, subcat, brand, cost, price, lead_time, reorder_qty in items:
            p_id = f"PRD-{prod_counter:03d}"
            sku = f"SKU-{cat_name[:3].upper()}-{prod_counter:03d}"
            margin_pct = round(((price - cost) / price) * 100, 2)
            products.append({
                "product_id": p_id,
                "sku": sku,
                "product_name": name,
                "category": cat_name,
                "sub_category": subcat,
                "brand": brand,
                "unit_cost": cost,
                "list_price": price,
                "target_margin_pct": margin_pct,
                "supplier_name": f"{brand} Global Logistics",
                "lead_time_days": lead_time,
                "reorder_quantity": reorder_qty
            })
            prod_counter += 1

    products_df = pd.DataFrame(products)
    products_raw_path = RAW_DATA_DIR / "products_raw.json"
    with open(products_raw_path, "w") as f:
        json.dump(products, f, indent=2)

    # 3. Time Series: Daily Transactions & Inventory Snapshots
    start_dt = datetime.strptime(SIMULATION_START_DATE, "%Y-%m-%d")
    end_dt = datetime.strptime(SIMULATION_END_DATE, "%Y-%m-%d")
    num_days = (end_dt - start_dt).days + 1

    # Base inventory state per store and product
    current_inventory = {}
    for store in STORES_DEF:
        s_id = store["store_id"]
        current_inventory[s_id] = {}
        for p in products:
            p_id = p["product_id"]
            # Initial inventory between 40 and 120 units
            current_inventory[s_id][p_id] = random.randint(50, 110)

    transactions = []
    inventory_snapshots = []
    restock_orders = []

    tx_counter = 100000
    restock_counter = 5000

    # Key Anomaly Dates to inject realistic demand spikes & supplier delays:
    # 1. Flash Sale Spike: 2026-03-14 to 2026-03-16 in Manhattan & Online Hub for Electronics
    # 2. Tech Wave Spike: 2026-05-01 to 2026-05-04 in SF & Austin
    # 3. Supplier Delay Stockout: 2026-04-10 to 2026-04-22 in Chicago for Footwear
    # 4. Weekend retail traffic patterns (Fridays, Saturdays, Sundays +40% volume)

    pending_deliveries = []  # (delivery_date, store_id, product_id, quantity)

    for day_idx in range(num_days):
        current_date = start_dt + timedelta(days=day_idx)
        date_str = current_date.strftime("%Y-%m-%d")
        weekday = current_date.weekday()
        is_weekend = weekday in (4, 5, 6)  # Fri, Sat, Sun

        # Process any arriving restock shipments today
        arrived = [d for d in pending_deliveries if d["delivery_date"] == date_str]
        pending_deliveries = [d for d in pending_deliveries if d["delivery_date"] != date_str]

        arrived_map = {}
        for arr in arrived:
            key = (arr["store_id"], arr["product_id"])
            arrived_map[key] = arrived_map.get(key, 0) + arr["quantity"]

        for store in STORES_DEF:
            s_id = store["store_id"]
            store_multiplier = 1.4 if store["store_type"] in ["Flagship", "Distribution Hub"] else 1.0

            for p in products:
                p_id = p["product_id"]
                p_cat = p["category"]
                lead_time = p["lead_time_days"]
                reorder_qty = p["reorder_quantity"]
                unit_cost = p["unit_cost"]
                list_price = p["list_price"]

                beg_inv = current_inventory[s_id][p_id]
                rec_units = arrived_map.get((s_id, p_id), 0)
                available_stock = beg_inv + rec_units

                # Calculate base sales velocity
                base_demand = random.uniform(1.2, 4.5) * store_multiplier
                if is_weekend:
                    base_demand *= 1.45

                # Anomaly 1: Flash sale spike in Electronics
                if "2026-03-14" <= date_str <= "2026-03-16" and p_cat == "Electronics" and s_id in ["STR-001", "STR-008"]:
                    base_demand *= 4.2  # Massive surge

                # Anomaly 2: Summer kick-off tech spike in West/South
                if "2026-05-01" <= date_str <= "2026-05-04" and s_id in ["STR-003", "STR-004"]:
                    base_demand *= 3.1

                # Actual sales constrained by available stock
                target_sales = int(np.random.poisson(base_demand))
                units_sold = min(target_sales, available_stock)

                end_inv = available_stock - units_sold
                current_inventory[s_id][p_id] = end_inv

                stockout = (end_inv == 0)
                safety_stock = int(p["lead_time_days"] * 2.2)
                reorder_point = safety_stock + int(p["lead_time_days"] * 2.8)

                # Stockout risk score (0 to 1)
                velocity_est = max(0.5, units_sold)
                days_of_supply = end_inv / velocity_est
                if days_of_supply <= 1.0:
                    stockout_risk_score = 0.95
                elif days_of_supply <= 3.0:
                    stockout_risk_score = 0.70
                elif days_of_supply <= 7.0:
                    stockout_risk_score = 0.40
                else:
                    stockout_risk_score = 0.05

                # Sell-through rate: Units Sold / (Beginning Inventory + Received)
                denom = beg_inv + rec_units
                str_pct = round((units_sold / denom * 100), 2) if denom > 0 else 0.0

                inventory_snapshots.append({
                    "snapshot_date": date_str,
                    "store_id": s_id,
                    "product_id": p_id,
                    "beginning_inventory": beg_inv,
                    "received_units": rec_units,
                    "units_sold": units_sold,
                    "ending_inventory": end_inv,
                    "inventory_value": round(end_inv * unit_cost, 2),
                    "safety_stock": safety_stock,
                    "reorder_point": reorder_point,
                    "stockout_flag": stockout,
                    "stockout_risk_score": stockout_risk_score,
                    "sell_through_rate": str_pct
                })

                # Check if reorder needed
                if end_inv <= reorder_point:
                    # Place a restock order if not already pending
                    is_already_pending = any(d["store_id"] == s_id and d["product_id"] == p_id for d in pending_deliveries)
                    if not is_already_pending:
                        # Anomaly 3: Injected supplier delay for Chicago Footwear in April
                        actual_delay = 0
                        if "2026-04-05" <= date_str <= "2026-04-20" and s_id == "STR-002" and p_cat == "Footwear":
                            actual_delay = 12  # Supplier port congestion delay!

                        delivery_dt = current_date + timedelta(days=(lead_time + actual_delay))
                        delivery_date_str = delivery_dt.strftime("%Y-%m-%d")

                        restock_counter += 1
                        restock_id = f"RST-{restock_counter}"
                        restock_orders.append({
                            "order_id": restock_id,
                            "order_date": date_str,
                            "expected_delivery_date": (current_date + timedelta(days=lead_time)).strftime("%Y-%m-%d"),
                            "actual_delivery_date": delivery_date_str,
                            "store_id": s_id,
                            "product_id": p_id,
                            "order_quantity": reorder_qty,
                            "unit_cost": unit_cost,
                            "total_cost": round(reorder_qty * unit_cost, 2),
                            "status": "Delayed" if actual_delay > 0 else "Delivered",
                            "lead_time_actual_days": lead_time + actual_delay
                        })

                        pending_deliveries.append({
                            "delivery_date": delivery_date_str,
                            "store_id": s_id,
                            "product_id": p_id,
                            "quantity": reorder_qty
                        })

                # If units were sold today, generate transactions
                if units_sold > 0:
                    # Split into 1 to 3 customer transaction baskets
                    baskets = min(units_sold, random.randint(1, 3))
                    units_remaining = units_sold
                    for b in range(baskets):
                        sub_units = units_remaining if b == baskets - 1 else max(1, units_remaining // baskets)
                        units_remaining -= sub_units
                        if sub_units <= 0:
                            break

                        tx_counter += 1
                        tx_id = f"TX-{tx_counter}"
                        hour = random.randint(10, 20)
                        minute = random.randint(0, 59)
                        tx_time = f"{date_str} {hour:02d}:{minute:02d}:00"

                        # Discount probability: 15% chance of 10% promo
                        disc = 0.10 if random.random() < 0.15 else 0.0
                        actual_unit_price = round(list_price * (1.0 - disc), 2)
                        gross_rev = round(actual_unit_price * sub_units, 2)
                        tot_cogs = round(unit_cost * sub_units, 2)
                        gm = round(gross_rev - tot_cogs, 2)
                        gm_pct = round((gm / gross_rev * 100), 2) if gross_rev > 0 else 0.0

                        channel = "Distribution Hub" if store["store_type"] == "Distribution Hub" else random.choice(["In-Store", "In-Store", "In-Store", "BOPIS", "Express Checkout"])
                        pay_method = random.choice(["Credit Card", "Apple Pay", "Credit Card", "Debit Card", "Cash"])

                        transactions.append({
                            "transaction_id": tx_id,
                            "timestamp": tx_time,
                            "date": date_str,
                            "store_id": s_id,
                            "product_id": p_id,
                            "units_sold": sub_units,
                            "unit_price": actual_unit_price,
                            "unit_cost": unit_cost,
                            "gross_revenue": gross_rev,
                            "cogs": tot_cogs,
                            "gross_margin": gm,
                            "gross_margin_pct": gm_pct,
                            "discount_pct": disc,
                            "payment_method": pay_method,
                            "channel": channel
                        })

    # Save to CSV in RAW_DATA_DIR
    tx_df = pd.DataFrame(transactions)
    inv_df = pd.DataFrame(inventory_snapshots)
    rst_df = pd.DataFrame(restock_orders)

    tx_path = RAW_DATA_DIR / "pos_transactions_raw.csv"
    inv_path = RAW_DATA_DIR / "inventory_snapshots_raw.csv"
    rst_path = RAW_DATA_DIR / "restock_orders_raw.csv"

    tx_df.to_csv(tx_path, index=False)
    inv_df.to_csv(inv_path, index=False)
    rst_df.to_csv(rst_path, index=False)

    logger.info(f"Dataset generated successfully:")
    logger.info(f" - Stores: {len(stores_df)}")
    logger.info(f" - Products: {len(products_df)}")
    logger.info(f" - Transactions: {len(tx_df):,}")
    logger.info(f" - Inventory Snapshots: {len(inv_df):,}")
    logger.info(f" - Restock Orders: {len(rst_df):,}")

    return {
        "stores": len(stores_df),
        "products": len(products_df),
        "transactions": len(tx_df),
        "inventory": len(inv_df),
        "restock": len(rst_df)
    }


if __name__ == "__main__":
    generate_raw_retail_datasets()
