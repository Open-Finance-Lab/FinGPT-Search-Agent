"""Tests for stock_analysis Timestamp key serialization fix."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pandas as pd


def test_safe_dict_with_timestamp_index():
    """Reproduces TypeError: keys must be str, not Timestamp."""
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler

    df = pd.DataFrame(
        {"Firm": ["Goldman", "Morgan"], "ToGrade": ["Buy", "Hold"]},
        index=pd.to_datetime(["2026-01-15", "2026-02-10"]),
    )
    handler = GetStockAnalysisHandler()
    result = handler._safe_dict(df)

    serialized = json.dumps(result, default=str)
    assert isinstance(serialized, str)

    for col_data in result.values():
        if isinstance(col_data, dict):
            for key in col_data:
                assert isinstance(key, str), f"Key {key!r} is {type(key).__name__}, expected str"


def test_safe_dict_with_timestamp_columns():
    """Financial statements use Timestamp column headers."""
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler

    df = pd.DataFrame(
        {"Revenue": [100, 200]},
        index=["row1", "row2"],
    )
    df.columns = pd.to_datetime(["2026-01-01"])

    handler = GetStockAnalysisHandler()
    result = handler._safe_dict(df)
    serialized = json.dumps(result, default=str)
    assert isinstance(serialized, str)

    for key in result:
        assert isinstance(key, str), f"Column key {key!r} is {type(key).__name__}, expected str"


def test_safe_dict_with_none():
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler
    handler = GetStockAnalysisHandler()
    assert handler._safe_dict(None) == {}


def test_safe_dict_with_empty_dataframe():
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler
    handler = GetStockAnalysisHandler()
    assert handler._safe_dict(pd.DataFrame()) == {}


def test_safe_dict_with_plain_dict():
    from mcp_server.handlers.stock_analysis import GetStockAnalysisHandler
    handler = GetStockAnalysisHandler()
    d = {"target_mean": 250.0}
    assert handler._safe_dict(d) == d
