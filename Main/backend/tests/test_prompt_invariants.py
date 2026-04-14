"""Locks the RATIO CLAIMS relevance gate and SHARE-COUNT UNITS rule in
`prompts/core.md`. Without them the agent pads responses with tangential
ratios so Validate runs on data the user never asked about, and displays
10-K "(in thousands)" share values as if they were full integer counts.
"""


def test_relevance_gate_present(core_prompt: str) -> None:
    assert "RELEVANCE GATE" in core_prompt, (
        "RATIO CLAIMS lost the RELEVANCE GATE header. Without it the agent "
        "reverts to padding responses with supported ratios and emitting "
        "report_claim for each, producing fake-validation on unrelated "
        "questions."
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
    for metric in ("EPS", "P/E", "market cap"):
        assert metric in core_prompt, (
            f"Prompt no longer names {metric!r} as an unsupported metric "
            f"in the relevance gate; agent may re-learn to pad claims."
        )


def test_share_count_unit_rule_present(core_prompt: str) -> None:
    assert "SHARE-COUNT UNITS" in core_prompt, (
        "DATA ACCURACY lost the SHARE-COUNT UNITS header. Without it the "
        "agent again displays 10-K 'in thousands' share values raw, which "
        "makes EPS arithmetic internally inconsistent on the user's screen."
    )
    assert "in thousands" in core_prompt.lower(), (
        "Prompt no longer cites the '(in thousands)' 10-K header that is "
        "the actual trigger for the unit mistake."
    )
