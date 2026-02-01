"""TradingView Scanner API client logic."""

import logging
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Scanner endpoints
SCANNER_URL = "https://scanner.tradingview.com/{market}/scan"

# Column mapping for technical indicators
TECHNICAL_COLUMNS = [
    "name", "description", "logoid", "update_mode", "type", "typespecs", "close", "pricescale", "minmov", "fractional", "minmove2", "change", "change_abs", "recommendation", "volume", "market_cap_basic",
    "RSI", "RSI[1]", "Stoch.K", "Stoch.D", "Stoch.K[1]", "Stoch.D[1]", "CCI20", "CCI20[1]", "ADX", "ADX+DI", "ADX-DI", "ADX+DI[1]", "ADX-DI[1]", "AO", "AO[1]", "AO[2]", "Mom", "Mom[1]", "MACD.macd", "MACD.signal", "Rec.Stoch.RSI", "Stoch.RSI.K", "Rec.WR", "W.R", "Rec.BBPower", "BBPower", "Rec.UO", "UO",
    "EMA10", "SMA10", "EMA20", "SMA20", "EMA30", "SMA30", "EMA50", "SMA50", "EMA100", "SMA100", "EMA200", "SMA200", "Rec.Ichimoku", "Ichimoku.BLine", "Rec.VWMA", "VWMA", "Rec.HullMA9", "HullMA9",
    "BB.lower", "BB.upper", "Pivot.M.Classic.S3", "Pivot.M.Classic.S2", "Pivot.M.Classic.S1", "Pivot.M.Classic.Middle", "Pivot.M.Classic.R1", "Pivot.M.Classic.R2", "Pivot.M.Classic.R3", "Pivot.M.Fibonacci.S3", "Pivot.M.Fibonacci.S2", "Pivot.M.Fibonacci.S1", "Pivot.M.Fibonacci.Middle", "Pivot.M.Fibonacci.R1", "Pivot.M.Fibonacci.R2", "Pivot.M.Fibonacci.R3", "Pivot.M.Camarilla.S3", "Pivot.M.Camarilla.S2", "Pivot.M.Camarilla.S1", "Pivot.M.Camarilla.Middle", "Pivot.M.Camarilla.R1", "Pivot.M.Camarilla.R2", "Pivot.M.Camarilla.R3", "Pivot.M.Woodie.S3", "Pivot.M.Woodie.S2", "Pivot.M.Woodie.S1", "Pivot.M.Woodie.Middle", "Pivot.M.Woodie.R1", "Pivot.M.Woodie.R2", "Pivot.M.Woodie.R3", "Pivot.M.DeMark.S1", "Pivot.M.DeMark.Middle", "Pivot.M.DeMark.R1", "open", "high", "low"
]

# Field mapping for internal tool keys to TradingView columns
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
    "change_percent": "change"
}

def get_market_from_exchange(exchange: str) -> str:
    """Map exchange to TradingView market folder."""
    exchange = exchange.upper()
    if exchange in ['BINANCE', 'KUCOIN', 'BYBIT', 'BITGET', 'OKX', 'COINBASE', 'GATEIO', 'HUOBI', 'BITFINEX']:
        return "crypto"
    if exchange in ['NASDAQ', 'NYSE', 'AMEX']:
        return "america"
    if exchange == 'BIST':
        return "turkey"
    return "world"

def call_scanner_api(market: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Perform request to TradingView Scanner API."""
    url = SCANNER_URL.format(market=market)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"TradingView Scanner API error: {e}")
        # Log payload for debugging
        logger.debug(f"Failed payload: {payload}")
        raise e

def get_coin_analysis(exchange: str, symbol: str, timeframe: str = "1D") -> Dict[str, Any]:
    """Fetch complete technical analysis for a symbol."""
    market = get_market_from_exchange(exchange)
    
    # TradingView expects symbol as "EXCHANGE:SYMBOL"
    full_symbol = f"{exchange.upper()}:{symbol.upper()}"
    
    payload = {
        "symbols": {
            "tickers": [full_symbol],
            "query": {"types": []}
        },
        "columns": TECHNICAL_COLUMNS
    }
    
    # Note: Timeframe handling in the scanner API is complex; 
    # usually done via specific column suffixes if needed, 
    # but the base columns return the default (usually 1D).
    
    data = call_scanner_api(market, payload)
    
    if not data.get("data"):
        return {}
        
    raw_item = data["data"][0]["d"]
    # Map raw list to dict using TECHNICAL_COLUMNS
    result = {TECHNICAL_COLUMNS[i]: raw_item[i] for i in range(len(TECHNICAL_COLUMNS))}
    
    # Internal normalization
    normalized = {}
    for internal_key, tv_key in FIELD_MAP.items():
        if tv_key in result:
            normalized[internal_key] = result[tv_key]
            
    # Add basics
    normalized["close"] = result.get("close")
    normalized["open"] = result.get("open")
    normalized["high"] = result.get("high")
    normalized["low"] = result.get("low")
    normalized["volume"] = result.get("volume")
    normalized["name"] = symbol
    
    return normalized

def get_timeframe_suffix(timeframe: str) -> str:
    """Get the TradingView column suffix for a given timeframe."""
    tf_map = {
        "1m": "|1", "5m": "|5", "15m": "|15", "30m": "|30",
        "1h": "|60", "2h": "|120", "4h": "|240",
        "1D": "", "1W": "|1W", "1M": "|1M"
    }
    return tf_map.get(timeframe, "")

def get_top_movers(exchange: str, list_type: str = "gainers", limit: int = 10, timeframe: str = "1D") -> List[Dict[str, Any]]:
    """Fetch top gainers or losers for an exchange."""
    market = get_market_from_exchange(exchange)
    suffix = get_timeframe_suffix(timeframe)
    
    # Use timeframe-specific change column
    change_col = f"change{suffix}" if suffix else "change"
    close_col = f"close{suffix}" if suffix else "close"
    volume_col = f"volume{suffix}" if suffix else "volume"
    
    sort_field = change_col
    sort_order = "desc" if list_type == "gainers" else "asc"
    
    payload = {
        "filter": [
            {"left": "exchange", "operation": "equal", "value": exchange.upper()},
            {"left": change_col, "operation": "nempty"}
        ],
        "options": {"lang": "en"},
        "markets": [market],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "description", close_col, change_col, volume_col],
        "sort": {"sort_by": sort_field, "order_order": sort_order},
        "range": [0, limit]
    }
    
    data = call_scanner_api(market, payload)
    
    results = []
    columns = payload["columns"]
    for row in data.get("data", []):
        item = {columns[i]: row["d"][i] for i in range(len(columns))}
        # Map to internal expected fields
        results.append({
            "symbol": item["name"],
            "name": item["description"],
            "close": item[close_col],
            "change_percent": item[change_col],
            "volume": item[volume_col]
        })
        
    return results

def get_bollinger_scan(exchange: str, timeframe: str = "1D", limit: int = 10) -> List[Dict[str, Any]]:
    """Find assets with tight Bollinger Bands (BB Width < 0.05)."""
    market = get_market_from_exchange(exchange)
    
    payload = {
        "filter": [
            {"left": "exchange", "operation": "equal", "value": exchange.upper()},
            {"left": "BB.width", "operation": "less", "value": 0.05}
        ],
        "options": {"lang": "en"},
        "markets": [market],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "description", "close", "BB.width", "volume"],
        "sort": {"sort_by": "BB.width", "order_order": "asc"},
        "range": [0, limit]
    }
    
    data = call_scanner_api(market, payload)
    
    results = []
    columns = payload["columns"]
    for row in data.get("data", []):
        item = {columns[i]: row["d"][i] for i in range(len(columns))}
        results.append({
            "symbol": item["name"],
            "name": item["description"],
            "close": item["close"],
            "BB_width": item["BB.width"],
            "volume": item["volume"]
        })
        
    return results

def get_rating_filter(exchange: str, rating: int = 0, timeframe: str = "1D", limit: int = 10) -> List[Dict[str, Any]]:
    """Filter assets by Bollinger Band rating."""
    market = get_market_from_exchange(exchange)
    
    payload = {
        "filter": [
            {"left": "exchange", "operation": "equal", "value": exchange.upper()},
            {"left": "BB.rating", "operation": "equal", "value": rating}
        ],
        "options": {"lang": "en"},
        "markets": [market],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "description", "close", "BB.rating", "volume"],
        "sort": {"sort_by": "volume", "order_order": "desc"},
        "range": [0, limit]
    }
    
    data = call_scanner_api(market, payload)
    
    results = []
    columns = payload["columns"]
    for row in data.get("data", []):
        item = {columns[i]: row["d"][i] for i in range(len(columns))}
        results.append({
            "symbol": item["name"],
            "name": item["description"],
            "close": item["close"],
            "BB_rating": item["BB.rating"],
            "volume": item["volume"]
        })
        
    return results
