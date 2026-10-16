"""
SQLAlchemy ORM models defining normalized relational schema & analytics tables.
Designed for high-throughput retail transactions, daily inventory snapshots, and real-time anomalies.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey, Boolean, Index, Text
)
from sqlalchemy.orm import relationship
from database.connection import Base


class Store(Base):
    __tablename__ = "dim_stores"

    store_id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    store_type = Column(String(50), nullable=False)  # Flagship, Downtown, Suburban, Mall, Express, Distribution Hub
    region = Column(String(50), nullable=False)      # East, Midwest, West, South
    city = Column(String(100), nullable=False)
    state = Column(String(10), nullable=False)
    square_feet = Column(Integer, default=15000)
    manager_name = Column(String(100), nullable=True)
    target_monthly_revenue = Column(Float, default=250000.0)
    is_active = Column(Boolean, default=True)

    # Relationships
    sales = relationship("SalesTransaction", back_populates="store", cascade="all, delete-orphan")
    inventory = relationship("InventorySnapshot", back_populates="store", cascade="all, delete-orphan")
    restock_orders = relationship("RestockOrder", back_populates="store", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "dim_products"

    product_id = Column(String(20), primary_key=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    product_name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # Electronics, Apparel, Home & Living, Footwear, Luxury
    sub_category = Column(String(50), nullable=False)
    brand = Column(String(100), nullable=False)
    unit_cost = Column(Float, nullable=False)
    list_price = Column(Float, nullable=False)
    target_margin_pct = Column(Float, nullable=False)
    supplier_name = Column(String(100), default="Apex Supply Global")
    lead_time_days = Column(Integer, default=7)
    reorder_quantity = Column(Integer, default=50)

    # Relationships
    sales = relationship("SalesTransaction", back_populates="product", cascade="all, delete-orphan")
    inventory = relationship("InventorySnapshot", back_populates="product", cascade="all, delete-orphan")
    restock_orders = relationship("RestockOrder", back_populates="product", cascade="all, delete-orphan")


class SalesTransaction(Base):
    __tablename__ = "fact_sales_transactions"

    transaction_id = Column(String(50), primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    store_id = Column(String(20), ForeignKey("dim_stores.store_id"), nullable=False, index=True)
    product_id = Column(String(20), ForeignKey("dim_products.product_id"), nullable=False, index=True)
    units_sold = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    gross_revenue = Column(Float, nullable=False)
    cogs = Column(Float, nullable=False)  # Cost of Goods Sold
    gross_margin = Column(Float, nullable=False)
    gross_margin_pct = Column(Float, nullable=False)
    discount_pct = Column(Float, default=0.0)
    payment_method = Column(String(30), default="Credit Card")  # Credit Card, Apple Pay, Cash, Debit
    channel = Column(String(30), default="In-Store")            # In-Store, BOPIS, Express Checkout

    # Relationships
    store = relationship("Store", back_populates="sales")
    product = relationship("Product", back_populates="sales")

    __table_args__ = (
        Index("idx_sales_store_date", "store_id", "date"),
        Index("idx_sales_prod_date", "product_id", "date"),
    )


class InventorySnapshot(Base):
    __tablename__ = "fact_daily_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    store_id = Column(String(20), ForeignKey("dim_stores.store_id"), nullable=False, index=True)
    product_id = Column(String(20), ForeignKey("dim_products.product_id"), nullable=False, index=True)
    beginning_inventory = Column(Integer, nullable=False)
    received_units = Column(Integer, default=0)
    units_sold = Column(Integer, default=0)
    ending_inventory = Column(Integer, nullable=False)
    inventory_value = Column(Float, nullable=False)
    safety_stock = Column(Integer, default=20)
    reorder_point = Column(Integer, default=40)
    stockout_flag = Column(Boolean, default=False)
    stockout_risk_score = Column(Float, default=0.0)  # 0.0 to 1.0 (1.0 = imminent stockout)
    sell_through_rate = Column(Float, default=0.0)    # % sell-through

    # Relationships
    store = relationship("Store", back_populates="inventory")
    product = relationship("Product", back_populates="inventory")

    __table_args__ = (
        Index("idx_inv_store_prod_date", "store_id", "product_id", "snapshot_date", unique=True),
    )


class RestockOrder(Base):
    __tablename__ = "fact_restock_orders"

    order_id = Column(String(50), primary_key=True)
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date, nullable=False)
    actual_delivery_date = Column(Date, nullable=True)
    store_id = Column(String(20), ForeignKey("dim_stores.store_id"), nullable=False)
    product_id = Column(String(20), ForeignKey("dim_products.product_id"), nullable=False)
    order_quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    status = Column(String(30), default="Delivered")  # Placed, In-Transit, Delivered, Delayed
    lead_time_actual_days = Column(Integer, nullable=True)

    # Relationships
    store = relationship("Store", back_populates="restock_orders")
    product = relationship("Product", back_populates="restock_orders")


class AnomalyEvent(Base):
    __tablename__ = "fact_anomaly_events"

    anomaly_id = Column(String(50), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    date = Column(Date, nullable=False, index=True)
    store_id = Column(String(20), ForeignKey("dim_stores.store_id"), nullable=False)
    product_id = Column(String(20), ForeignKey("dim_products.product_id"), nullable=False)
    metric_name = Column(String(50), nullable=False)  # Sales Velocity, Demand Spike, Inventory Deficit
    observed_value = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    z_score = Column(Float, nullable=False)
    anomaly_type = Column(String(50), nullable=False)  # Demand Spike, Stockout Alert, Restock Lag
    severity = Column(String(20), nullable=False)      # Critical, High, Medium, Info
    is_resolved = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)


class KpiDailySnapshot(Base):
    __tablename__ = "fact_kpi_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    store_id = Column(String(20), ForeignKey("dim_stores.store_id"), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    total_revenue = Column(Float, nullable=False)
    total_cogs = Column(Float, nullable=False)
    gross_margin = Column(Float, nullable=False)
    gross_margin_pct = Column(Float, nullable=False)
    units_sold = Column(Integer, nullable=False)
    average_inventory_units = Column(Float, nullable=False)
    average_inventory_value = Column(Float, nullable=False)
    sell_through_rate = Column(Float, nullable=False)
    inventory_turnover = Column(Float, nullable=False)
    stockout_count = Column(Integer, default=0)
    stockout_rate_pct = Column(Float, default=0.0)
