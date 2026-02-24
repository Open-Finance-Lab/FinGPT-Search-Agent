"""Tests for get_options_summary handler."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pandas as pd
from mcp_server.handlers.options_summary import aggregate_chain


def _make_chain(call_vols, put_vols, call_oi, put_oi):
    """Create a mock option chain with calls and puts DataFrames."""
    calls = pd.DataFrame({
        "volume": call_vols,
        "openInterest": call_oi,
        "strike": [100.0] * len(call_vols),
    })
    puts = pd.DataFrame({
        "volume": put_vols,
        "openInterest": put_oi,
        "strike": [100.0] * len(put_vols),
    })

    class Chain:
        pass

    c = Chain()
    c.calls = calls
    c.puts = puts
    return c


def test_aggregate_chain_basic():
    chain = _make_chain(
        call_vols=[100, 200, float("nan")],
        put_vols=[50, 150, 100],
        call_oi=[1000, 2000, 500],
        put_oi=[800, 1200, 400],
    )
    result = aggregate_chain(chain, "2026-03-21")
    assert result["expiration"] == "2026-03-21"
    assert result["call_volume"] == 300
    assert result["put_volume"] == 300
    assert result["total_volume"] == 600
    assert result["call_oi"] == 3500
    assert result["put_oi"] == 2400
    assert result["total_oi"] == 5900
    assert abs(result["put_call_ratio"] - 1.0) < 0.01


def test_aggregate_chain_zero_call_volume():
    chain = _make_chain(
        call_vols=[0, 0],
        put_vols=[100, 200],
        call_oi=[0, 0],
        put_oi=[500, 600],
    )
    result = aggregate_chain(chain, "2026-03-21")
    assert result["call_volume"] == 0
    assert result["put_volume"] == 300
    assert result["put_call_ratio"] is None


def test_aggregate_chain_all_nan():
    chain = _make_chain(
        call_vols=[float("nan")],
        put_vols=[float("nan")],
        call_oi=[float("nan")],
        put_oi=[float("nan")],
    )
    result = aggregate_chain(chain, "2026-03-21")
    assert result["call_volume"] == 0
    assert result["put_volume"] == 0
    assert result["total_volume"] == 0


def test_aggregate_chain_json_serializable():
    """Verify the output is always JSON-serializable."""
    chain = _make_chain(
        call_vols=[100, float("nan")],
        put_vols=[200, 300],
        call_oi=[1000, 500],
        put_oi=[800, 200],
    )
    result = aggregate_chain(chain, "2026-03-21")
    serialized = json.dumps(result)
    assert isinstance(serialized, str)
