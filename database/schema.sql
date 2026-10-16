-- ==============================================================================
-- Schema Definition: Realtime Sales Performance & Inventory Optimization
-- Relational 3NF Transactional Core & Dimensional Star Schema Data Mart
-- Compatible with PostgreSQL 14+ and SQLite 3.35+
-- ==============================================================================

-- 1. STORE DIMENSION
CREATE TABLE IF NOT EXISTS dim_stores (
    store_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    store_type VARCHAR(50) NOT NULL, -- Flagship, Downtown, Suburban, Mall, Express, Distribution Hub
    region VARCHAR(50) NOT NULL,     -- East, Midwest, West, South
    city VARCHAR(100) NOT NULL,
    state VARCHAR(10) NOT NULL,
    square_feet INTEGER DEFAULT 15000,
    manager_name VARCHAR(100),
    target_monthly_revenue NUMERIC(12, 2) DEFAULT 250000.00,
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. PRODUCT DIMENSION
CREATE TABLE IF NOT EXISTS dim_products (
    product_id VARCHAR(20) PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    sub_category VARCHAR(50) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL,
    list_price NUMERIC(10, 2) NOT NULL,
    target_margin_pct NUMERIC(5, 2) NOT NULL,
    supplier_name VARCHAR(100) DEFAULT 'Apex Supply Global',
    lead_time_days INTEGER DEFAULT 7,
    reorder_quantity INTEGER DEFAULT 50
);

-- 3. SALES TRANSACTIONS FACT TABLE
CREATE TABLE IF NOT EXISTS fact_sales_transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    date DATE NOT NULL,
    store_id VARCHAR(20) NOT NULL REFERENCES dim_stores(store_id),
    product_id VARCHAR(20) NOT NULL REFERENCES dim_products(product_id),
    units_sold INTEGER NOT NULL CHECK (units_sold > 0),
    unit_price NUMERIC(10, 2) NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL,
    gross_revenue NUMERIC(12, 2) NOT NULL,
    cogs NUMERIC(12, 2) NOT NULL,
    gross_margin NUMERIC(12, 2) NOT NULL,
    gross_margin_pct NUMERIC(6, 2) NOT NULL,
    discount_pct NUMERIC(5, 2) DEFAULT 0.00,
    payment_method VARCHAR(30) DEFAULT 'Credit Card',
    channel VARCHAR(30) DEFAULT 'In-Store'
);

CREATE INDEX IF NOT EXISTS idx_sales_store_date ON fact_sales_transactions(store_id, date);
CREATE INDEX IF NOT EXISTS idx_sales_prod_date ON fact_sales_transactions(product_id, date);

-- 4. DAILY INVENTORY FACT TABLE
CREATE TABLE IF NOT EXISTS fact_daily_inventory (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    store_id VARCHAR(20) NOT NULL REFERENCES dim_stores(store_id),
    product_id VARCHAR(20) NOT NULL REFERENCES dim_products(product_id),
    beginning_inventory INTEGER NOT NULL,
    received_units INTEGER DEFAULT 0,
    units_sold INTEGER DEFAULT 0,
    ending_inventory INTEGER NOT NULL,
    inventory_value NUMERIC(12, 2) NOT NULL,
    safety_stock INTEGER DEFAULT 20,
    reorder_point INTEGER DEFAULT 40,
    stockout_flag BOOLEAN DEFAULT FALSE,
    stockout_risk_score NUMERIC(5, 2) DEFAULT 0.00,
    sell_through_rate NUMERIC(6, 2) DEFAULT 0.00,
    CONSTRAINT uq_store_prod_date UNIQUE (store_id, product_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_inv_store_prod_date ON fact_daily_inventory(store_id, product_id, snapshot_date);

-- 5. RESTOCK ORDERS FACT TABLE
CREATE TABLE IF NOT EXISTS fact_restock_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    order_date DATE NOT NULL,
    expected_delivery_date DATE NOT NULL,
    actual_delivery_date DATE,
    store_id VARCHAR(20) NOT NULL REFERENCES dim_stores(store_id),
    product_id VARCHAR(20) NOT NULL REFERENCES dim_products(product_id),
    order_quantity INTEGER NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL,
    total_cost NUMERIC(12, 2) NOT NULL,
    status VARCHAR(30) DEFAULT 'Delivered',
    lead_time_actual_days INTEGER
);

-- 6. ANOMALY DETECTION LOG TABLE
CREATE TABLE IF NOT EXISTS fact_anomaly_events (
    anomaly_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    date DATE NOT NULL,
    store_id VARCHAR(20) NOT NULL REFERENCES dim_stores(store_id),
    product_id VARCHAR(20) NOT NULL REFERENCES dim_products(product_id),
    metric_name VARCHAR(50) NOT NULL,
    observed_value NUMERIC(10, 2) NOT NULL,
    expected_value NUMERIC(10, 2) NOT NULL,
    z_score NUMERIC(6, 2) NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    notes TEXT
);

-- 7. PRE-AGGREGATED KPI SNAPSHOT TABLE (For instant Executive Dashboard queries)
CREATE TABLE IF NOT EXISTS fact_kpi_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    store_id VARCHAR(20) NOT NULL REFERENCES dim_stores(store_id),
    category VARCHAR(50) NOT NULL,
    total_revenue NUMERIC(12, 2) NOT NULL,
    total_cogs NUMERIC(12, 2) NOT NULL,
    gross_margin NUMERIC(12, 2) NOT NULL,
    gross_margin_pct NUMERIC(6, 2) NOT NULL,
    units_sold INTEGER NOT NULL,
    average_inventory_units NUMERIC(10, 2) NOT NULL,
    average_inventory_value NUMERIC(12, 2) NOT NULL,
    sell_through_rate NUMERIC(6, 2) NOT NULL,
    inventory_turnover NUMERIC(6, 2) NOT NULL,
    stockout_count INTEGER DEFAULT 0,
    stockout_rate_pct NUMERIC(6, 2) DEFAULT 0.00
);
