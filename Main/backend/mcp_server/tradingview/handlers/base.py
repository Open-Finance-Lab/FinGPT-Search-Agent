"""Base handler for TradingView MCP tools."""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import mcp.types as types

from mcp_server.handlers.base import ToolHandler, ToolContext
from mcp_server.cache import TimedCache


logger = logging.getLogger(__name__)


# Relevant technical fields for numerical accuracy
RELEVANT_TECHNICAL_FIELDS = [
    # Price data
    'symbol', 'close', 'open', 'high', 'low', 'volume',
    # Bollinger Bands
    'BB_upper', 'BB_middle', 'BB_lower', 'BB_width', 'BB_rating',
    # Oscillators
    'RSI', 'MACD', 'MACD_signal', 'MACD_histogram', 'Stochastic_K', 'Stochastic_D', 'ADX',
    # Moving Averages
    'SMA_20', 'SMA_50', 'SMA_200', 'EMA_20', 'EMA_50', 'EMA_200',
    # Volume indicators
    'volume_24h', 'volume_change',
    # Momentum
    'momentum', 'change_percent', 'change',
    # Metadata
    'exchange', 'timeframe', 'timestamp', 'name', 'data', 'assets', 'gainers', 'losers', 'analysis'
]


class TradingViewBaseHandler(ToolHandler):
    """Base class for TradingView handlers with shared caching logic."""

    def __init__(self, cache_ttl_seconds: int = 600):
        """Initialize handler with cache.

        Args:
            cache_ttl_seconds: Cache TTL in seconds (default: 10 minutes)
        """
        self._cache = TimedCache(ttl_seconds=cache_ttl_seconds)

    def _get_cache_key(self, **params) -> str:
        """Generate cache key from parameters.

        Args:
            **params: Parameters to hash

        Returns:
            Cache key string
        """
        # Sort params for consistent hashing
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{self.__class__.__name__}:{param_hash}"

    def _filter_numerical_fields(self, data: Any) -> Any:
        """Filter data to include only relevant technical fields.

        Args:
            data: Raw data from TradingView

        Returns:
            Filtered data with only relevant fields
        """
        if isinstance(data, dict):
            return {
                k: self._filter_numerical_fields(v)
                for k, v in data.items()
                if k in RELEVANT_TECHNICAL_FIELDS or k in ['error', 'message']
            }
        elif isinstance(data, list):
            return [self._filter_numerical_fields(item) for item in data]
        else:
            return data

    def _enforce_numerical_types(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce correct numerical types for known fields.

        Args:
            data: Data dictionary

        Returns:
            Data with enforced types
        """
        # Float fields
        float_fields = {
            'close', 'open', 'high', 'low', 'volume',
            'BB_upper', 'BB_middle', 'BB_lower', 'BB_width',
            'RSI', 'MACD', 'MACD_signal', 'MACD_histogram',
            'Stochastic_K', 'Stochastic_D', 'ADX',
            'SMA_20', 'SMA_50', 'SMA_200', 'EMA_20', 'EMA_50', 'EMA_200',
            'change_percent', 'change', 'momentum'
        }

        # Integer fields
        int_fields = {'BB_rating', 'volume_24h'}

        result = data.copy()

        for field, value in data.items():
            if value is None:
                continue

            try:
                if field in float_fields:
                    result[field] = float(value)
                elif field in int_fields:
                    result[field] = int(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert {field}={value} to number: {e}")

        return result

    def _log_large_response(self, data: List[Dict], threshold: int = 50) -> None:
        """Log warning if response is large.

        Args:
            data: Response data list
            threshold: Warning threshold
        """
        if len(data) > threshold:
            logger.warning(
                f"{self.__class__.__name__} returned {len(data)} items "
                f"(threshold: {threshold}). Consider using smaller limits."
            )

    async def _call_tradingview(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call TradingView Scanner API.

        Args:
            tool_name: Name of the TradingView tool
            params: Parameters for the tool

        Returns:
            Response data from TradingView
        """
        import asyncio
        from mcp_server.tradingview import scanner_api
        
        exchange = params.get("exchange", "BINANCE")
        symbol = params.get("symbol")
        
        try:
            if tool_name == "get_coin_analysis":
                data = await asyncio.to_thread(
                    scanner_api.get_coin_analysis,
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=params.get("timeframe", "1D")
                )
                return {"data": data}
            
            elif tool_name == "get_top_gainers":
                data = await asyncio.to_thread(
                    scanner_api.get_top_movers,
                    exchange=exchange,
                    list_type="gainers",
                    limit=params.get("limit", 10),
                    timeframe=params.get("timeframe", "1D")
                )
                return {"data": data}
                
            elif tool_name == "get_top_losers":
                data = await asyncio.to_thread(
                    scanner_api.get_top_movers,
                    exchange=exchange,
                    list_type="losers",
                    limit=params.get("limit", 10),
                    timeframe=params.get("timeframe", "1D")
                )
                return {"data": data}
            
            elif tool_name == "get_bollinger_scan":
                data = await asyncio.to_thread(
                    scanner_api.get_bollinger_scan,
                    exchange=exchange,
                    timeframe=params.get("timeframe", "1D"),
                    limit=params.get("limit", 10)
                )
                return {"data": data}

            elif tool_name == "get_rating_filter":
                data = await asyncio.to_thread(
                    scanner_api.get_rating_filter,
                    exchange=exchange,
                    rating=params.get("rating", 0),
                    timeframe=params.get("timeframe", "1D"),
                    limit=params.get("limit", 10)
                )
                return {"data": data}
            
            # TODO: Implement get_consecutive_candles, get_advanced_candle_pattern
            logger.warning(f"Tool {tool_name} not yet fully implemented in real scanner")
            return {"data": []}

        except Exception as e:
            logger.error(f"TradingView call failed: {e}")
            return {"error": str(e), "data": []}
