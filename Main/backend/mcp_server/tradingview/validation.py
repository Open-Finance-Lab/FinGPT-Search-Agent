"""Input validation for TradingView MCP server."""

import re
from typing import Optional


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


# Exchange validation sets
VALID_CRYPTO_EXCHANGES = {
    'KUCOIN', 'BINANCE', 'BYBIT', 'BITGET', 'OKX', 'COINBASE',
    'GATEIO', 'HUOBI', 'BITFINEX', 'KRAKEN', 'MEXC', 'GEMINI', 'BITSTAMP'
}

VALID_STOCK_EXCHANGES = {
    'NASDAQ', 'NYSE', 'BIST', 'LSE', 'HKEX', 'TSE'
}

# Timeframe validation
VALID_TIMEFRAMES = {
    '1m', '5m', '15m', '30m', '1h', '2h', '4h',
    '1D', '1W', '1M'
}


def validate_exchange(exchange: Optional[str], market_type: str = 'crypto') -> str:
    """Validate exchange parameter.

    Args:
        exchange: The exchange name to validate
        market_type: Type of market - 'crypto' or 'stock'

    Returns:
        The validated and uppercase exchange name

    Raises:
        ValidationError: If exchange is invalid
    """
    if not exchange:
        raise ValidationError("Exchange is required")

    exchange = exchange.upper().strip()

    if market_type == 'crypto':
        valid_set = VALID_CRYPTO_EXCHANGES
        market_name = "crypto"
    elif market_type == 'stock':
        valid_set = VALID_STOCK_EXCHANGES
        market_name = "stock"
    else:
        raise ValidationError(f"Invalid market_type: {market_type}")

    if exchange not in valid_set:
        raise ValidationError(
            f"Invalid {market_name} exchange: {exchange}. "
            f"Must be one of: {', '.join(sorted(valid_set))}"
        )

    return exchange


def validate_timeframe(timeframe: Optional[str]) -> str:
    """Validate timeframe parameter.

    Args:
        timeframe: The timeframe string to validate

    Returns:
        The validated timeframe string

    Raises:
        ValidationError: If timeframe is invalid
    """
    if not timeframe:
        raise ValidationError("Timeframe is required")

    timeframe = timeframe.strip()

    if timeframe not in VALID_TIMEFRAMES:
        raise ValidationError(
            f"Invalid timeframe: {timeframe}. "
            f"Must be one of: {', '.join(sorted(VALID_TIMEFRAMES))}"
        )

    return timeframe


def validate_bollinger_rating(rating: int) -> int:
    """Validate Bollinger Band rating parameter.

    Args:
        rating: The rating value to validate

    Returns:
        The validated rating value

    Raises:
        ValidationError: If rating is out of bounds
    """
    if not isinstance(rating, int):
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            raise ValidationError(f"Rating must be an integer, got: {rating}")

    if rating < -3 or rating > 3:
        raise ValidationError(
            f"Rating must be between -3 and +3, got: {rating}"
        )

    return rating


def validate_crypto_symbol(symbol: Optional[str]) -> str:
    """Validate cryptocurrency trading pair symbol.

    Args:
        symbol: The symbol to validate (e.g., 'BTCUSDT')

    Returns:
        The validated and uppercase symbol

    Raises:
        ValidationError: If symbol is invalid
    """
    if not symbol:
        raise ValidationError("Symbol is required")

    symbol = symbol.upper().strip()

    # Crypto pairs typically: 3-10 uppercase letters (e.g., BTCUSDT, ETHUSDT)
    if not re.match(r'^[A-Z]{3,10}$', symbol):
        raise ValidationError(
            f"Invalid symbol format: {symbol}. "
            "Expected format: BTCUSDT, ETHUSDT, etc."
        )

    return symbol


def validate_limit(limit: Optional[int], max_limit: int = 100) -> int:
    """Validate limit parameter for result counts.

    Args:
        limit: The limit value to validate
        max_limit: Maximum allowed limit

    Returns:
        The validated limit value

    Raises:
        ValidationError: If limit is invalid
    """
    if limit is None:
        return 10  # Default limit

    if not isinstance(limit, int):
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            raise ValidationError(f"Limit must be an integer, got: {limit}")

    if limit < 1:
        raise ValidationError(f"Limit must be at least 1, got: {limit}")

    if limit > max_limit:
        raise ValidationError(
            f"Limit cannot exceed {max_limit}, got: {limit}"
        )

    return limit
