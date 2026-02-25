"""Tests for stock_financials Timestamp column key serialization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pandas as pd
from mcp_server.handlers.stock_financials import _safe_financials_to_dict


def test_financials_timestamp_columns():
    """Financial statement DataFrames use Timestamp column headers (quarterly dates)."""
    df = pd.DataFrame(
        [[100_000, 200_000], [10_000, 20_000]],
        index=["Revenue", "NetIncome"],
        columns=pd.to_datetime(["2025-09-30", "2025-12-31"]),
    )
    result = _safe_financials_to_dict(df)
    serialized = json.dumps(result, default=str)
    assert isinstance(serialized, str)

    for key in result:
        assert isinstance(key, str), f"Column key {key!r} is {type(key).__name__}, expected str"


def test_financials_empty_dataframe():
    assert _safe_financials_to_dict(pd.DataFrame()) == {}


def test_financials_none():
    assert _safe_financials_to_dict(None) == {}
