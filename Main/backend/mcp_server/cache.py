"""TTL cache for Yahoo Finance data."""

import threading
from datetime import datetime, timedelta
from typing import Any, Optional


class TimedCache:
    """Simple TTL cache for yfinance Ticker objects.

    Thread-safe cache with automatic expiration based on TTL.
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache.

        Args:
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if datetime.now() - timestamp < self.ttl:
                    return value
                # Expired, remove it
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Cache value with current timestamp.

        Also evicts expired entries to prevent unbounded growth.

        Args:
            key: Cache key
            value: Value to cache
        """
        now = datetime.now()
        with self._lock:
            # Evict expired entries on write to prevent memory leaks
            expired = [k for k, (_, ts) in self._cache.items() if now - ts >= self.ttl]
            for k in expired:
                del self._cache[k]
            self._cache[key] = (value, now)

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
