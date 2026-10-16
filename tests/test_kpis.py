"""
Test suite for retail KPI computations and analytical queries.
"""

import pytest
from analytics.kpi_engine import RetailKpiEngine
from database.connection import init_db
from etl.pipeline import RetailETLPipeline


@pytest.fixture(scope="module", autouse=True)
def init_warehouse():
    pipeline = RetailETLPipeline()
    pipeline.run()


def test_executive_summary():
    engine = RetailKpiEngine()
    summary = engine.get_executive_summary()

    assert summary["total_revenue"] > 0
    assert summary["gross_margin"] > 0
    assert 0.0 <= summary["gross_margin_pct"] <= 100.0
    assert 0.0 <= summary["sell_through_rate"] <= 100.0
    assert summary["inventory_turnover"] > 0
    assert summary["total_transactions"] > 0


def test_store_leaderboard():
    engine = RetailKpiEngine()
    stores = engine.get_store_leaderboard()

    assert len(stores) == 8
    # Sorted by revenue descending
    revenues = [s["total_revenue"] for s in stores]
    assert revenues == sorted(revenues, reverse=True)


def test_category_breakdown():
    engine = RetailKpiEngine()
    cats = engine.get_category_performance()

    assert len(cats) >= 5
    total_rev = sum(c["revenue"] for c in cats)
    assert total_rev > 0
