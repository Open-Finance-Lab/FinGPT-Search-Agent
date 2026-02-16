"""Tests for research configuration."""
import pytest


def test_research_config_exists():
    from datascraper.models_config import RESEARCH_CONFIG
    assert isinstance(RESEARCH_CONFIG, dict)


def test_research_config_has_required_keys():
    from datascraper.models_config import RESEARCH_CONFIG
    required = {"planner_model", "research_model", "max_iterations", "max_sub_questions", "parallel_searches"}
    assert required.issubset(RESEARCH_CONFIG.keys())


def test_research_config_defaults():
    from datascraper.models_config import RESEARCH_CONFIG
    assert RESEARCH_CONFIG["planner_model"] == "gpt-5-mini"
    assert RESEARCH_CONFIG["max_iterations"] == 3
    assert RESEARCH_CONFIG["max_sub_questions"] == 5
    assert RESEARCH_CONFIG["parallel_searches"] is True


def test_get_research_config_returns_copy():
    from datascraper.models_config import get_research_config
    config = get_research_config()
    config["max_iterations"] = 999
    from datascraper.models_config import RESEARCH_CONFIG
    assert RESEARCH_CONFIG["max_iterations"] == 3  # Original unchanged
