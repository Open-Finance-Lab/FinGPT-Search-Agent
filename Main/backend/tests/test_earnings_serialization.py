"""Tests for earnings_info Timestamp key serialization fix."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Stub out heavy third-party dependencies that earnings_info imports transitively
# so the test suite stays lightweight and fast.
for _mod in ("yfinance", "mcp", "mcp.types", "mcp.server"):
    sys.modules.setdefault(_mod, MagicMock())

import json
import pandas as pd
from mcp_server.handlers.earnings_info import _safe_df_to_dict


def test_safe_df_to_dict_with_timestamp_index():
    """earnings_dates DataFrame has DatetimeIndex."""
    df = pd.DataFrame(
        {"EPS Estimate": [3.25, 3.50], "Reported EPS": [3.30, None]},
        index=pd.to_datetime(["2026-01-30", "2026-04-30"]),
    )
    result = _safe_df_to_dict(df)
    serialized = json.dumps(result, default=str)
    assert isinstance(serialized, str)

    for col_data in result.values():
        if isinstance(col_data, dict):
            for key in col_data:
                assert isinstance(key, str)


def test_safe_df_to_dict_none():
    assert _safe_df_to_dict(None) == {}


def test_safe_df_to_dict_empty():
    assert _safe_df_to_dict(pd.DataFrame()) == {}


def test_safe_df_to_dict_plain_dict():
    d = {"next_earnings": "2026-04-30"}
    assert _safe_df_to_dict(d) == d
