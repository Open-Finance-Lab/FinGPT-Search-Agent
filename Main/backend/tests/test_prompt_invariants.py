"""Prompt-invariant tests for Layer 1 Validate.

These lock in two guardrails that were added after an EPS question
produced a response where:
  1. Diluted Shares was displayed as the raw 10-K "in thousands" value
     (15,812,547) instead of ~15.8B, making the on-screen arithmetic
     Net Income / Diluted Shares internally inconsistent with the EPS.
  2. The agent padded the answer with a "Financial Context (TTM)"
     block that computed the three supported ratios, then emitted
     report_claim for each so that Validate rendered "All 3 ratios
     verified" on a question the user actually asked about EPS.

The fix is in the system prompt; these tests fail loudly if the
guardrail language is removed or weakened, so the regression cannot
recur silently the next time someone reshuffles core.md.
"""

from pathlib import Path

import pytest

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "core.md"
)


@pytest.fixture(scope="module")
def core_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def test_relevance_gate_present(core_prompt: str) -> None:
    """The RATIO CLAIMS section must tell the agent NOT to volunteer the
    three supported ratios just so Validate has something to run."""
    assert "RELEVANCE GATE" in core_prompt, (
        "RATIO CLAIMS lost the RELEVANCE GATE header. Without it the agent "
        "reverts to padding responses with supported ratios and emitting "
        "report_claim for each, producing fake-validation on questions it "
        "was never asked."
    )
    lowered = core_prompt.lower()
    assert "financial context" in lowered, (
        "Prompt no longer names the 'Financial Context' padding pattern by "
        "example; the specific phrase is what the agent was producing."
    )
    assert "emit zero claims" in lowered, (
        "Prompt no longer states the zero-emission outcome for unsupported "
        "metrics (EPS, P/E, etc.). The agent needs an explicit instruction."
    )


def test_unsupported_metrics_enumerated(core_prompt: str) -> None:
    """The agent has to know which common metrics are out of scope,
    otherwise it treats report_claim as an always-on sidecar and emits
    tangentially related ratios for them."""
    for metric in ("EPS", "P/E", "market cap"):
        assert metric in core_prompt, (
            f"Prompt no longer names {metric!r} as an unsupported metric "
            f"in the relevance gate; agent may re-learn to pad claims."
        )


def test_share_count_unit_rule_present(core_prompt: str) -> None:
    """Guardrail that caught the 15,812,547 vs 15.8B Diluted Shares bug."""
    assert "SHARE-COUNT UNITS" in core_prompt, (
        "DATA ACCURACY lost the SHARE-COUNT UNITS header. Without it the "
        "agent again displays 10-K 'in thousands' share values raw, which "
        "makes EPS arithmetic internally inconsistent on the user's screen."
    )
    lowered = core_prompt.lower()
    assert "in thousands" in lowered, (
        "Prompt no longer cites the '(in thousands)' 10-K header that is "
        "the actual trigger for the unit mistake."
    )
    assert "15,812,547" in core_prompt, (
        "Prompt no longer carries the Apple-FY2023 diluted-shares example "
        "that grounds the unit rule. A concrete example matters more than "
        "an abstract rule for LLM compliance."
    )


def test_supported_ratios_still_named(core_prompt: str) -> None:
    """Defense-in-depth: prompt must still enumerate exactly the three
    ratios the engine supports (keeps prompt and tool.py in lockstep)."""
    for ratio in ("accounting_equation", "gross_margin", "current_ratio"):
        assert ratio in core_prompt
