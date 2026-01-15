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

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            self._cache[key] = (value, datetime.now())

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
