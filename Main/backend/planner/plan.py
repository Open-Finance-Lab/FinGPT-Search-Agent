from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ExecutionPlan:
    """Structured execution plan output by the Planner."""
    skill_name: str
    tools_allowed: Optional[List[str]] = None      # None = all tools (fallback)
    max_turns: int = 10
    instructions: Optional[str] = None             # If set, replaces PromptBuilder output
