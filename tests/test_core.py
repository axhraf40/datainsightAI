"""Fast tests for the parts of the pipeline that don't need an LLM."""

from pathlib import Path

import pandas as pd
import pytest

from data_cleaner import clean_dataset
from rag.rag_engine import analyze_dataset

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "ecommerce_sales.csv"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_csv(SAMPLE)


def test_sample_dataset_loads(df):
    assert len(df) > 0
    assert {"Order ID", "Order Date", "Category", "Sales"} <= set(df.columns)


def test_rag_maps_columns_and_suggests_questions(df):
    profile = analyze_dataset(df, "ecommerce_sales.csv")
    assert profile["row_count"] == len(df)
    assert profile["column_mappings"], "expected at least one semantic column mapping"
    assert profile["suggested_questions"], "expected suggested questions"


def test_cleaner_keeps_rows_and_returns_report(df):
    dirty = pd.concat([df, df.head(5)], ignore_index=True)  # add duplicates
    cleaned, report = clean_dataset(dirty, "dirty.csv")
    assert isinstance(cleaned, pd.DataFrame)
    assert len(cleaned) <= len(dirty)
    assert report is not None
