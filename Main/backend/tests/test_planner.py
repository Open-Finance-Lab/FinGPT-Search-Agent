import pytest
from planner.planner import Planner
from planner.plan import ExecutionPlan


class TestPlanner:
    def setup_method(self):
        self.planner = Planner()

    def test_plan_returns_execution_plan(self):
        plan = self.planner.plan(
            user_query="summarize this page",
            system_prompt="[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n- From https://example.com:\nSome content here",
            domain="example.com",
        )
        assert isinstance(plan, ExecutionPlan)

    def test_summarize_plan_no_tools(self):
        plan = self.planner.plan(
            user_query="what does this article say?",
            system_prompt="[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n- From https://example.com:\nArticle about earnings...",
            domain="example.com",
        )
        assert plan.skill_name == "summarize_page"
        assert plan.tools_allowed == []
        assert plan.max_turns == 1
        assert plan.instructions is not None
        assert "Article about earnings" in plan.instructions

    def test_stock_price_plan(self):
        plan = self.planner.plan(
            user_query="what is AAPL stock price?",
            system_prompt=None,
            domain="finance.yahoo.com",
        )
        assert plan.skill_name == "stock_fundamentals"
        assert "get_stock_info" in plan.tools_allowed
        assert plan.max_turns == 3
        assert plan.instructions is None

    def test_fallback_plan(self):
        plan = self.planner.plan(
            user_query="find me biotech investment ideas",
            system_prompt=None,
            domain=None,
        )
        assert plan.skill_name == "web_research"
        assert plan.tools_allowed is None
        assert plan.max_turns == 10

    def test_prescraped_detection(self):
        plan = self.planner.plan(
            user_query="summarize this",
            system_prompt="[CURRENT PAGE CONTENT - Already scraped, do NOT re-scrape]:\n- From url:\nContent",
            domain=None,
        )
        assert plan.skill_name == "summarize_page"

    def test_no_prescraped_detection(self):
        plan = self.planner.plan(
            user_query="summarize this",
            system_prompt="Some other system prompt without page content",
            domain=None,
        )
        assert plan.skill_name == "web_research"

    def test_options_plan(self):
        plan = self.planner.plan(
            user_query="show me options volume for AVGO",
            system_prompt=None,
            domain="finance.yahoo.com",
        )
        assert plan.skill_name == "options_analysis"
        assert "get_options_summary" in plan.tools_allowed

    def test_earnings_plan(self):
        plan = self.planner.plan(
            user_query="when are MSFT earnings and what's the EPS estimate?",
            system_prompt=None,
            domain=None,
        )
        assert plan.skill_name == "financial_statements"
        assert "get_earnings_info" in plan.tools_allowed

    def test_technical_analysis_plan(self):
        plan = self.planner.plan(
            user_query="what's the RSI for BTC?",
            system_prompt=None,
            domain=None,
        )
        assert plan.skill_name == "technical_analysis"
