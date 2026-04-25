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


def test_math_delimiter_rule_canonical(core_prompt: str) -> None:
    """Step 1.1 lock: the prompt must teach \\(...\\) inline / $$...$$ display
    and explicitly forbid single $...$ for math. The renderer
    (frontend/src/modules/markdownRenderer.js) does not parse single $ as
    math because currency mentions collide; if the prompt drifts back to
    "Use $ for inline math" the agent's math output stops rendering."""
    assert "\\(...\\)" in core_prompt and "$$...$$" in core_prompt, (
        "core.md no longer shows the canonical math delimiter pair "
        "\\(...\\) for inline / $$...$$ for display."
    )
    assert "single $" in core_prompt.lower() or "single $...$" in core_prompt.lower(), (
        "core.md no longer explicitly forbids single $...$ for math, "
        "which is what triggers currency-vs-math collision in the renderer."
    )


def test_formula_inputs_audit_only(core_prompt: str) -> None:
    """Step 1.3 lock: formula_inputs is decorative in every flow — the engine
    compares claimed_value to XBRL ground truth directly. A previous version
    of the prompt said the field was "informational only in the
    validate-user-claim case", which misled readers into believing Q&A
    flow used it for verification. axioms/engine.py never reads it."""
    lowered = core_prompt.lower()
    assert "formula_inputs" in core_prompt
    forbidden = "informational only and does not drive the verdict"
    assert forbidden not in lowered, (
        "core.md still scopes the formula_inputs audit-only rule to the "
        "validate-user-claim case. The engine never reads formula_inputs in "
        "ANY flow; the unscoped wording is the load-bearing one."
    )
    assert "audit" in lowered and "never drives the verdict in any flow" in lowered, (
        "core.md no longer says formula_inputs is audit-only across all "
        "flows. Without that, readers may assume Q&A verification depends "
        "on it."
    )


def test_validate_intent_cues_cover_frontend_regex(core_prompt: str) -> None:
    """Step 1.4 lock: every cue in intent.js::VALIDATION_INTENT_RE must also
    appear in core.md Rule 1, so the frontend's auto-fire trigger and the
    agent's claimed_value-pinning rule cannot disagree about what counts as
    a validate-user-claim intent. If a cue is added to the regex it must
    be added to the prompt in the same commit."""
    lowered = core_prompt.lower()
    required_cues = [
        "validate",
        "verify",
        "fact-check",
        "double-check",
        "sanity-check",
        "cross-check",
    ]
    for cue in required_cues:
        assert cue in lowered, (
            f"core.md Rule 1 no longer lists {cue!r} as a validate-user-claim "
            f"phrasing. The frontend regex in intent.js still fires on it, "
            f"so the agent will be auto-validated without knowing to pin "
            f"claimed_value to the user's number."
        )


def test_report_claim_docstring_mirrors_relevance_gate() -> None:
    """Step 1.2 lock: the report_claim function-tool docstring is what the
    model reads when deciding to call the tool. It must echo the RELEVANCE
    GATE and Rule 1 from core.md, NOT the old "Call this EXACTLY ONCE for
    every supported ratio" wording that drove the agent to pad responses."""
    from pathlib import Path

    tool_path = Path(__file__).resolve().parent.parent / "axioms" / "tool.py"
    src = tool_path.read_text(encoding="utf-8")
    assert "EXACTLY ONCE for every supported ratio" not in src, (
        "axioms/tool.py::report_claim docstring still tells the model to "
        "emit a claim for every supported ratio it presents. This contradicts "
        "core.md's RELEVANCE GATE and is the channel the model trusts most."
    )
    assert "RELEVANCE GATE" in src, (
        "axioms/tool.py::report_claim docstring no longer references the "
        "RELEVANCE GATE. The docstring and prompt must agree on when to "
        "call this tool."
    )
    assert "user's stated number" in src, (
        "axioms/tool.py::report_claim docstring no longer states that "
        "claimed_value must be the user's number in validate-user-claim "
        "flows. Without it, the agent substitutes its own corrected value "
        "and silently breaks Validate."
    )
