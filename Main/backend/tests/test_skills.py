import pytest
from planner.plan import ExecutionPlan
from planner.skills.base import BaseSkill


class TestExecutionPlan:
    def test_creation_with_defaults(self):
        plan = ExecutionPlan(skill_name="test")
        assert plan.skill_name == "test"
        assert plan.tools_allowed is None
        assert plan.max_turns == 10
        assert plan.instructions is None

    def test_zero_tool_plan(self):
        plan = ExecutionPlan(
            skill_name="summarize_page",
            tools_allowed=[],
            max_turns=1,
            instructions="Summarize this content.",
        )
        assert plan.tools_allowed == []
        assert plan.max_turns == 1

    def test_filtered_tool_plan(self):
        plan = ExecutionPlan(
            skill_name="stock_fundamentals",
            tools_allowed=["get_stock_info", "get_stock_history", "calculate"],
            max_turns=3,
        )
        assert len(plan.tools_allowed) == 3
        assert "get_stock_info" in plan.tools_allowed


class TestBaseSkill:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseSkill()

    def test_concrete_skill_must_implement_methods(self):
        class IncompleteSkill(BaseSkill):
            pass

        with pytest.raises(TypeError):
            IncompleteSkill()
