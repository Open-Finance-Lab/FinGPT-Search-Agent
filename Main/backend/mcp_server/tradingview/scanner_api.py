"""TradingView Scanner API client logic.

Uses tradingview-ta for individual symbol analysis and
tradingview-screener for exchange-wide screening queries.
"""

import logging
from typing import Any, Dict, List

from tradingview_ta import Interval, get_multiple_analysis
from tradingview_screener import Query, col

logger = logging.getLogger(__name__)

# Field mapping for internal tool keys to TradingView indicator names
FIELD_MAP = {
    "RSI": "RSI",
    "MACD": "MACD.macd",
    "MACD_signal": "MACD.signal",
    "BB_upper": "BB.upper",
    "BB_lower": "BB.lower",
    "SMA_20": "SMA20",
    "SMA_50": "SMA50",
    "SMA_200": "SMA200",
    "EMA_20": "EMA20",
    "EMA_50": "EMA50",
    "EMA_200": "EMA200",
    "volume_24h": "volume",
    "change_percent": "change",
}

# Map our timeframe strings to tradingview-ta Interval constants
INTERVAL_MAP = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "30m": Interval.INTERVAL_30_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "2h": Interval.INTERVAL_2_HOURS,
    "4h": Interval.INTERVAL_4_HOURS,
    "1D": Interval.INTERVAL_1_DAY,
    "1W": Interval.INTERVAL_1_WEEK,
    "1M": Interval.INTERVAL_1_MONTH,
}

# Map timeframe to tradingview-screener column suffix
SCREENER_SUFFIX_MAP = {
    "1m": "|1", "5m": "|5", "15m": "|15", "30m": "|30",
    "1h": "|60", "2h": "|120", "4h": "|240",
    "1D": "", "1W": "|1W", "1M": "|1M",
}


def get_market_from_exchange(exchange: str) -> str:
    """Map exchange to TradingView screener market name."""
    exchange = exchange.upper()
    if exchange in [
        "BINANCE", "KUCOIN", "BYBIT", "BITGET", "OKX",
        "COINBASE", "GATEIO", "HUOBI", "BITFINEX",
    ]:
        return "crypto"
    if exchange in ["NASDAQ", "NYSE", "AMEX"]:
        return "america"
    if exchange == "BIST":
        return "turkey"
    return "america"


def _get_interval(timeframe: str) -> str:
    """Convert our timeframe string to a tradingview-ta Interval constant."""
    return INTERVAL_MAP.get(timeframe, Interval.INTERVAL_1_DAY)


def _get_suffix(timeframe: str) -> str:
    """Get the tradingview-screener column suffix for a timeframe."""
    return SCREENER_SUFFIX_MAP.get(timeframe, "")


def get_coin_analysis(
    exchange: str, symbol: str, timeframe: str = "1D"
) -> Dict[str, Any]:
    """Fetch complete technical analysis for a symbol.

    Uses tradingview-ta's get_multiple_analysis() for reliable data retrieval.
    """
    market = get_market_from_exchange(exchange)
    interval = _get_interval(timeframe)
    full_symbol = f"{exchange.upper()}:{symbol.upper()}"

    try:
        analyses = get_multiple_analysis(
            screener=market,
            interval=interval,
            symbols=[full_symbol],
        )
    except Exception as e:
        logger.error(f"tradingview-ta analysis failed for {full_symbol}: {e}")
        raise

    analysis = analyses.get(full_symbol)
    if analysis is None:
        logger.warning(f"No analysis data returned for {full_symbol}")
        return {}

    indicators = analysis.indicators or {}

    # Build normalized result using FIELD_MAP
    normalized: Dict[str, Any] = {}
    for internal_key, tv_key in FIELD_MAP.items():
        val = indicators.get(tv_key)
        if val is not None:
            normalized[internal_key] = val

    # Add price basics
    normalized["close"] = indicators.get("close")
    normalized["open"] = indicators.get("open")
    normalized["high"] = indicators.get("high")
    normalized["low"] = indicators.get("low")
    normalized["volume"] = indicators.get("volume")
    normalized["name"] = symbol.upper()

    # Add recommendation summaries (bonus data from the library)
    normalized["recommendation"] = analysis.summary.get("RECOMMENDATION")
    normalized["oscillators_recommendation"] = analysis.oscillators.get(
        "RECOMMENDATION"
    )
    normalized["moving_averages_recommendation"] = analysis.moving_averages.get(
        "RECOMMENDATION"
    )

    return normalized


def get_top_movers(
    exchange: str,
    list_type: str = "gainers",
    limit: int = 10,
    timeframe: str = "1D",
) -> List[Dict[str, Any]]:
    """Fetch top gainers or losers for an exchange.

    Uses tradingview-screener Query builder for reliable scanning.
    """
    market = get_market_from_exchange(exchange)
    suffix = _get_suffix(timeframe)

    change_col = f"change{suffix}" if suffix else "change"
    close_col = f"close{suffix}" if suffix else "close"
    volume_col = f"volume{suffix}" if suffix else "volume"

    ascending = list_type != "gainers"

    try:
        _count, df = (
            Query()
            .select("name", "description", close_col, change_col, volume_col)
            .set_markets(market)
            .where(
                col("exchange") == exchange.upper(),
                col(change_col).not_empty(),
            )
            .order_by(change_col, ascending=ascending)
            .limit(limit)
            .get_scanner_data()
        )
    except Exception as e:
        logger.error(f"tradingview-screener top_movers failed: {e}")
        raise

    results = []
    for _, row in df.iterrows():
        results.append({
            "symbol": row.get("name", ""),
            "name": row.get("description", ""),
            "close": row.get(close_col),
            "change_percent": row.get(change_col),
            "volume": row.get(volume_col),
        })

    return results


def get_bollinger_scan(
    exchange: str, timeframe: str = "1D", limit: int = 10
) -> List[Dict[str, Any]]:
    """Find assets with tight Bollinger Bands (BBW < 0.05).

    Uses tradingview-screener to fetch BB components, then computes
    Bollinger Band Width in Python as (BB.upper - BB.lower) / SMA20.
    """
    market = get_market_from_exchange(exchange)
    suffix = _get_suffix(timeframe)

    close_col = f"close{suffix}" if suffix else "close"
    sma20_col = f"SMA20{suffix}" if suffix else "SMA20"
    bb_upper_col = f"BB.upper{suffix}" if suffix else "BB.upper"
    bb_lower_col = f"BB.lower{suffix}" if suffix else "BB.lower"
    volume_col = f"volume{suffix}" if suffix else "volume"

    # Fetch more than needed so we can filter by computed BBW
    fetch_limit = max(limit * 5, 100)

    try:
        _count, df = (
            Query()
            .select(
                "name", "description", close_col,
                sma20_col, bb_upper_col, bb_lower_col, volume_col,
            )
            .set_markets(market)
            .where(
                col("exchange") == exchange.upper(),
                col(sma20_col).not_empty(),
                col(bb_upper_col).not_empty(),
                col(bb_lower_col).not_empty(),
            )
            .order_by(volume_col, ascending=False)
            .limit(fetch_limit)
            .get_scanner_data()
        )
    except Exception as e:
        logger.error(f"tradingview-screener bollinger_scan failed: {e}")
        raise

    results = []
    for _, row in df.iterrows():
        sma20 = row.get(sma20_col)
        bb_upper = row.get(bb_upper_col)
        bb_lower = row.get(bb_lower_col)

        if sma20 is None or bb_upper is None or bb_lower is None or sma20 == 0:
            continue

        bbw = (bb_upper - bb_lower) / sma20

        if bbw < 0.05:
            results.append({
                "symbol": row.get("name", ""),
                "name": row.get("description", ""),
                "close": row.get(close_col),
                "BB_width": round(bbw, 6),
                "volume": row.get(volume_col),
            })

    # Sort by BB_width ascending (tightest first)
    results.sort(key=lambda x: x.get("BB_width", float("inf")))
    return results[:limit]


def get_rating_filter(
    exchange: str, rating: int = 0, timeframe: str = "1D", limit: int = 10
) -> List[Dict[str, Any]]:
    """Filter assets by computed Bollinger Band position rating.

    Rating scale (-3 to +3):
      +3: price above upper BB
      +2: price in upper 33% of bands
      +1: price in middle-upper 33%
       0: price near middle (SMA20)
      -1: price in middle-lower 33%
      -2: price in lower 33% of bands
      -3: price below lower BB

    Uses tradingview-screener to fetch BB data, computes rating in Python.
    """
    market = get_market_from_exchange(exchange)
    suffix = _get_suffix(timeframe)

    close_col = f"close{suffix}" if suffix else "close"
    sma20_col = f"SMA20{suffix}" if suffix else "SMA20"
    bb_upper_col = f"BB.upper{suffix}" if suffix else "BB.upper"
    bb_lower_col = f"BB.lower{suffix}" if suffix else "BB.lower"
    volume_col = f"volume{suffix}" if suffix else "volume"

    # Fetch a larger batch to filter by computed rating
    fetch_limit = max(limit * 10, 200)

    try:
        _count, df = (
            Query()
            .select(
                "name", "description", close_col,
                sma20_col, bb_upper_col, bb_lower_col, volume_col,
            )
            .set_markets(market)
            .where(
                col("exchange") == exchange.upper(),
                col(bb_upper_col).not_empty(),
                col(bb_lower_col).not_empty(),
                col(close_col).not_empty(),
            )
            .order_by(volume_col, ascending=False)
            .limit(fetch_limit)
            .get_scanner_data()
        )
    except Exception as e:
        logger.error(f"tradingview-screener rating_filter failed: {e}")
        raise

    results = []
    for _, row in df.iterrows():
        close = row.get(close_col)
        bb_upper = row.get(bb_upper_col)
        bb_lower = row.get(bb_lower_col)

        if close is None or bb_upper is None or bb_lower is None:
            continue

        band_range = bb_upper - bb_lower
        if band_range == 0:
            continue

        # Compute position within bands as 0..1 (0 = lower, 1 = upper)
        position = (close - bb_lower) / band_range

        # Map position to rating scale -3 to +3
        if close > bb_upper:
            computed_rating = 3
        elif position >= 0.67:
            computed_rating = 2
        elif position >= 0.5:
            computed_rating = 1
        elif position >= 0.33:
            computed_rating = 0
        elif position >= 0.17:
            computed_rating = -1
        elif close >= bb_lower:
            computed_rating = -2
        else:
            computed_rating = -3

        if computed_rating == rating:
            results.append({
                "symbol": row.get("name", ""),
                "name": row.get("description", ""),
                "close": close,
                "BB_rating": computed_rating,
                "volume": row.get(volume_col),
            })

    # Sort by volume descending
    results.sort(key=lambda x: x.get("volume") or 0, reverse=True)
    return results[:limit]
