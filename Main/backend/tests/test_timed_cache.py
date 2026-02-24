"""Tests for TimedCache max_entries eviction and TTL behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from datetime import timedelta
from mcp_server.cache import TimedCache


def test_basic_get_set():
    cache = TimedCache(ttl_seconds=60, max_entries=10)
    cache.set("AAPL", {"price": 150})
    assert cache.get("AAPL") == {"price": 150}


def test_expired_entry_returns_none():
    cache = TimedCache(ttl_seconds=0, max_entries=10)
    cache.set("AAPL", {"price": 150})
    # TTL of 0 seconds means immediately expired
    time.sleep(0.01)
    assert cache.get("AAPL") is None


def test_max_entries_evicts_oldest():
    cache = TimedCache(ttl_seconds=60, max_entries=3)
    cache.set("A", 1)
    cache.set("B", 2)
    cache.set("C", 3)
    # Cache is at capacity
    assert len(cache) == 3

    # Adding a 4th should evict the oldest (A)
    cache.set("D", 4)
    assert len(cache) == 3
    assert cache.get("A") is None
    assert cache.get("B") == 2
    assert cache.get("C") == 3
    assert cache.get("D") == 4


def test_max_entries_one():
    cache = TimedCache(ttl_seconds=60, max_entries=1)
    cache.set("A", 1)
    cache.set("B", 2)
    assert len(cache) == 1
    assert cache.get("A") is None
    assert cache.get("B") == 2


def test_update_existing_key_does_not_grow():
    cache = TimedCache(ttl_seconds=60, max_entries=3)
    cache.set("A", 1)
    cache.set("B", 2)
    cache.set("C", 3)
    # Update existing key - should not trigger eviction of others
    cache.set("A", 10)
    assert len(cache) == 3
    assert cache.get("A") == 10
    assert cache.get("B") == 2
    assert cache.get("C") == 3


def test_expired_entries_evicted_on_set():
    cache = TimedCache(ttl_seconds=1, max_entries=100)
    cache.set("A", 1)
    cache.set("B", 2)
    time.sleep(1.1)
    # Both A and B are expired; setting C should evict them
    cache.set("C", 3)
    assert len(cache) == 1
    assert cache.get("C") == 3


def test_clear():
    cache = TimedCache(ttl_seconds=60, max_entries=10)
    cache.set("A", 1)
    cache.set("B", 2)
    cache.clear()
    assert len(cache) == 0
    assert cache.get("A") is None


def test_default_max_entries():
    """Verify default max_entries is 50."""
    cache = TimedCache()
    assert cache.max_entries == 50
    assert cache.ttl == timedelta(seconds=300)


def test_burst_of_unique_keys():
    """Simulate burst of diverse ticker queries - the real-world scenario."""
    cache = TimedCache(ttl_seconds=60, max_entries=5)
    for i in range(20):
        cache.set(f"TICKER_{i}", {"data": f"value_{i}"})

    # Should never exceed max_entries
    assert len(cache) == 5
    # Only the last 5 should survive
    for i in range(15):
        assert cache.get(f"TICKER_{i}") is None
    for i in range(15, 20):
        assert cache.get(f"TICKER_{i}") == {"data": f"value_{i}"}
