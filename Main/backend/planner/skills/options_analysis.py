import re
from typing import Optional, List
from .base import BaseSkill

_PATTERNS = [
    r"\boptions?\b.*(volume|chain|flow|data|activity|summary)",
    r"\b(put|call)[/ ](call|put)\b",
    r"\bopen interest\b",
    r"\b(options?|puts?|calls?)\b.*(expir|strike|premium)",
    r"\bimplied volatility\b",
    r"\biv\b.*\b(rank|percentile)\b",
    r"\boptions? (for|on|of)\b",
    r"\b(total|aggregate) (options?|puts?|calls?) (volume|oi)\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


class OptionsAnalysisSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "options_analysis"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return ["get_options_summary", "get_options_chain", "calculate"]

    @property
    def max_turns(self) -> int:
        return 5

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        for p in _COMPILED:
            if p.search(query):
                return 0.8
        return 0.0
