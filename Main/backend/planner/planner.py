import logging
from typing import Optional
from .plan import ExecutionPlan
from .skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

_PRESCRAPED_MARKER = "[CURRENT PAGE CONTENT"


class Planner:
    """
    Analyzes a user query and produces an ExecutionPlan.

    v1: Code heuristics (no LLM call). Fast, deterministic, zero API cost.
    """

    def __init__(self):
        self._registry = SkillRegistry()

    def plan(
        self,
        user_query: str,
        system_prompt: Optional[str],
        domain: Optional[str],
    ) -> ExecutionPlan:
        has_prescraped = self._has_prescraped_content(system_prompt)
        pre_scraped_content = self._extract_prescraped(system_prompt) if has_prescraped else None

        skill = self._registry.best_match(
            user_query,
            has_prescraped=has_prescraped,
            domain=domain,
        )

        instructions = skill.build_instructions(pre_scraped_content=pre_scraped_content)

        plan = ExecutionPlan(
            skill_name=skill.name,
            tools_allowed=skill.tools_allowed,
            max_turns=skill.max_turns,
            instructions=instructions,
        )

        logger.info(
            f"[Planner] plan={plan.skill_name} tools={len(plan.tools_allowed) if plan.tools_allowed is not None else 'ALL'} "
            f"turns={plan.max_turns} has_instructions={'yes' if plan.instructions else 'no'}"
        )
        return plan

    @staticmethod
    def _has_prescraped_content(system_prompt: Optional[str]) -> bool:
        if not system_prompt:
            return False
        return _PRESCRAPED_MARKER in system_prompt

    @staticmethod
    def _extract_prescraped(system_prompt: Optional[str]) -> Optional[str]:
        if not system_prompt:
            return None

        idx = system_prompt.find(_PRESCRAPED_MARKER)
        if idx == -1:
            return None

        content = system_prompt[idx:]
        return content
