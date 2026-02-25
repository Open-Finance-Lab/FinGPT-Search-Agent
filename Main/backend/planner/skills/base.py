from abc import ABC, abstractmethod
from typing import Optional, List


class BaseSkill(ABC):
    """Abstract base for all skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    @property
    @abstractmethod
    def tools_allowed(self) -> Optional[List[str]]:
        """Tool names this skill may use. None = all, [] = none."""
        ...

    @property
    @abstractmethod
    def max_turns(self) -> int:
        """Maximum agent turns for this skill."""
        ...

    @abstractmethod
    def matches(self, query: str, *, has_prescraped: bool, domain: str | None) -> float:
        """
        Return a confidence score 0.0-1.0 that this skill handles the query.
        0.0 = definitely not, 1.0 = perfect match.
        """
        ...

    def build_instructions(self, *, pre_scraped_content: str | None = None) -> str | None:
        """
        Return custom instructions, or None to use the default PromptBuilder.
        Override in skills that need a focused prompt (e.g. SummarizePageSkill).
        """
        return None
