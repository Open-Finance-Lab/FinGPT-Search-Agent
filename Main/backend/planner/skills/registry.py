import logging
from typing import Optional
from .base import BaseSkill
from .summarize_page import SummarizePageSkill
from .stock_fundamentals import StockFundamentalsSkill
from .options_analysis import OptionsAnalysisSkill
from .financial_statements import FinancialStatementsSkill
from .technical_analysis import TechnicalAnalysisSkill
from .web_research import WebResearchSkill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Maintains a ranked list of skills and selects the best match."""

    def __init__(self):
        self.skills: list[BaseSkill] = [
            SummarizePageSkill(),
            StockFundamentalsSkill(),
            OptionsAnalysisSkill(),
            FinancialStatementsSkill(),
            TechnicalAnalysisSkill(),
            WebResearchSkill(),
        ]

    def best_match(
        self,
        query: str,
        *,
        has_prescraped: bool,
        domain: str | None,
    ) -> BaseSkill:
        """Return the skill with the highest confidence score."""
        best_skill = self.skills[-1]
        best_score = 0.0

        for skill in self.skills:
            score = skill.matches(query, has_prescraped=has_prescraped, domain=domain)
            if score > best_score:
                best_score = score
                best_skill = skill

        logger.info(f"[SkillRegistry] Selected '{best_skill.name}' (score={best_score:.2f}) for query: {query[:80]}")
        return best_skill
