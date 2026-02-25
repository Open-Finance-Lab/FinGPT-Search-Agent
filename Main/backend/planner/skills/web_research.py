from typing import Optional, List
from .base import BaseSkill


class WebResearchSkill(BaseSkill):
    """Fallback skill — current full-autonomy behavior."""

    @property
    def name(self) -> str:
        return "web_research"

    @property
    def tools_allowed(self) -> Optional[List[str]]:
        return None

    @property
    def max_turns(self) -> int:
        return 10

    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        return 0.1
