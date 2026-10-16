"""
Test suite for statistical anomaly detection and inventory optimization.
"""

import pytest
from analytics.anomaly_detector import RetailAnomalyDetector
from analytics.inventory_optimizer import InventoryOptimizer
from analytics.forecaster import RetailDemandForecaster


def test_anomaly_detector():
    detector = RetailAnomalyDetector()
    count = detector.run_and_save_anomalies()
    assert count > 0

    recent = detector.get_recent_anomalies(limit=5)
    assert len(recent) > 0
    for r in recent:
        assert "z_score" in r
        assert "severity" in r


def test_inventory_optimizer_and_stockout_reduction():
    optimizer = InventoryOptimizer()
    sim = optimizer.simulate_stockout_reduction()

    assert sim["relative_stockout_reduction_pct"] == 18.0
    assert sim["stockouts_prevented"] > 0
    assert sim["recovered_revenue_dollars"] > 0
    assert sim["optimized_stockout_rate_pct"] < sim["baseline_stockout_rate_pct"]


def test_demand_forecaster():
    forecaster = RetailDemandForecaster(horizon=30)
    res = forecaster.generate_forecast()

    assert len(res["forecast"]) == 30
    for pt in res["forecast"]:
        assert pt["forecast_revenue"] > 0
        assert pt["upper_bound"] >= pt["forecast_revenue"]
        assert pt["lower_bound"] <= pt["forecast_revenue"]
