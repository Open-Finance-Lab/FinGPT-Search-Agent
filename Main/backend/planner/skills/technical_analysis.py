import re
from typing import Optional, List
from .base import BaseSkill

_PATTERNS = [
    r"\bRSI\b",
    r"\bMACD\b",
    r"\b(bollinger|bb) band",
    r"\bmoving average\b",
    r"\b(SMA|EMA)\b",
    r"\bADX\b",
    r"\bstochastic\b",
    r"\btechnical (analysis|indicator)",
    r"\b(support|resistance) (level|line|zone)\b",
    r"\b(overbought|oversold)\b",
    r"\b(golden|death) cross\b",
    r"\bcandlestick pattern\b",
    r"\bcandle pattern\b",
    r"\b(top |biggest )?(gainers?|losers?)\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


class TechnicalAnalysisSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "technical_analysis"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return [
            "get_coin_analysis",
            "get_top_gainers",
            "get_top_losers",
            "get_bollinger_scan",
            "get_rating_filter",
            "get_consecutive_candles",
            "get_advanced_candle_pattern",
            "calculate",
        ]

    @property
    def max_turns(self) -> int:
        return 3

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        for p in _COMPILED:
            if p.search(query):
                return 0.8
        return 0.0
