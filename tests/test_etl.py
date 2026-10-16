"""
Test suite for ETL extraction, transformation, and loading.
"""

import pytest
import pandas as pd
from etl.generator import generate_raw_retail_datasets
from etl.extract import RetailDataExtractor
from etl.transform import RetailDataTransformer


@pytest.fixture(scope="module")
def setup_raw_data():
    """Generates synthetic data for tests."""
    stats = generate_raw_retail_datasets()
    assert stats["stores"] > 0
    assert stats["products"] > 0
    assert stats["transactions"] > 0
    assert stats["inventory"] > 0
    return stats


def test_extraction(setup_raw_data):
    extractor = RetailDataExtractor()
    raw = extractor.extract_all()

    assert not raw["stores"].empty
    assert not raw["products"].empty
    assert not raw["transactions"].empty
    assert not raw["inventory"].empty
    assert not raw["restock"].empty


def test_transformation(setup_raw_data):
    extractor = RetailDataExtractor()
    transformer = RetailDataTransformer()

    raw = extractor.extract_all()
    clean = transformer.transform_all(raw)

    tx = clean["transactions"]
    inv = clean["inventory"]

    # Mathematical assertions
    assert (tx["gross_revenue"] >= 0).all()
    assert (tx["cogs"] >= 0).all()
    assert (tx["gross_margin"] == (tx["gross_revenue"] - tx["cogs"]).round(2)).all()

    # Inventory balance
    assert (inv["ending_inventory"] >= 0).all()
    assert (inv["sell_through_rate"] >= 0.0).all()
    assert (inv["sell_through_rate"] <= 100.0).all()

    # Pre-aggregated KPIs
    kpis = clean["kpis"]
    assert not kpis.empty
    assert "sell_through_rate" in kpis.columns
    assert "inventory_turnover" in kpis.columns
