import re
from typing import Optional, List
from .base import BaseSkill

_PATTERNS = [
    r"\brevenue\b",
    r"\b(net )?income\b",
    r"\bearnings\b",
    r"\b(income|balance|cash flow) statement\b",
    r"\bbalance sheet\b",
    r"\bEPS\b",
    r"\bEBITDA\b",
    r"\bprofit margin\b",
    r"\boperating (income|expenses?|margin)\b",
    r"\bgross (profit|margin)\b",
    r"\bfree cash flow\b",
    r"\bdebt[- ]to[- ]equity\b",
    r"\b(quarterly|annual) (results|report|financials)\b",
    r"\b(next|upcoming|when).{0,15}earnings\b",
    r"\bgrowth (rate|estimate|projection)\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


class FinancialStatementsSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "financial_statements"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return ["get_stock_financials", "get_earnings_info", "calculate"]

    @property
    def max_turns(self) -> int:
        return 3

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        for p in _COMPILED:
            if p.search(query):
                return 0.8
        return 0.0
