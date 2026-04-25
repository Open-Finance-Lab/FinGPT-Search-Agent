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


def test_no_playwright_leak_in_core(core_prompt: str) -> None:
    """Step 2.1 lock: core.md must not name 'Playwright' anywhere — neither
    in tool descriptions nor in the security rule. The actual tool names
    (navigate_to_url, click_element, extract_page_content) stay; only the
    library brand is scrubbed. Otherwise the prompt simultaneously names
    Playwright and tells the agent never to disclose it — a confused signal
    that increases leak risk rather than reduces it."""
    assert "playwright" not in core_prompt.lower(), (
        "core.md still mentions 'Playwright'. The catalog/section header "
        "should use neutral 'Browser tools' wording so the prompt does not "
        "simultaneously name and forbid the brand."
    )
    # The functional tool names must still be present.
    for tool_name in ("navigate_to_url", "click_element", "extract_page_content"):
        assert tool_name in core_prompt, (
            f"Tool name {tool_name!r} disappeared from core.md when "
            f"Playwright references were scrubbed; the agent now has no "
            f"way to learn this tool exists."
        )


def test_user_provided_context_security_rule(core_prompt: str) -> None:
    """Step 2.4 lock: SECURITY section must instruct the model to treat
    everything inside `[USER-PROVIDED CONTEXT ...]` as data, not
    instructions. Without this rule the API-supplied system_prompt is an
    open injection channel — the wrapping in PromptBuilder.build is
    necessary but not sufficient on its own."""
    lowered = core_prompt.lower()
    assert "user-provided context" in lowered, (
        "core.md SECURITY section no longer references the USER-PROVIDED "
        "CONTEXT block. The wrapping in PromptBuilder.build relies on a "
        "matching prompt-side rule telling the model the block is data."
    )
    assert "data, not instructions" in lowered, (
        "core.md no longer says USER-PROVIDED CONTEXT is data, not "
        "instructions. The exact phrasing is what the wrapping in "
        "PromptBuilder.build mirrors; if either drifts, prompt injection "
        "via the system_prompt parameter regains its effect."
    )


def test_xbrl_and_ratio_claims_have_precedence_rules(core_prompt: str) -> None:
    """Step 2.5 lock: both XBRL VERIFICATION and RATIO CLAIMS sections
    must carry an explicit precedence rule at the top so the agent knows
    when to use which. Without it the MSFT validate-user-claim demo
    flips between flows non-deterministically (P1.10)."""
    # Locate both sections; precedence rule must appear within ~400 chars
    # of each header so it sits at the TOP of the section. Anchor on the
    # full header strings so we don't match cross-references in surrounding
    # prose (e.g. "use the RATIO CLAIMS flow below instead").
    idx_xbrl = core_prompt.find("XBRL VERIFICATION:")
    idx_ratio = core_prompt.find("RATIO CLAIMS (output protocol")
    assert idx_xbrl != -1, "XBRL VERIFICATION section header disappeared"
    assert idx_ratio != -1, "RATIO CLAIMS section header disappeared"

    xbrl_head = core_prompt[idx_xbrl:idx_xbrl + 400]
    ratio_head = core_prompt[idx_ratio:idx_ratio + 400]
    assert "PRECEDENCE" in xbrl_head, (
        "XBRL VERIFICATION section is missing the PRECEDENCE rule at the "
        "top — the agent will continue to flip between this manual-table "
        "flow and the RATIO CLAIMS flow on validate-user-claim prompts."
    )
    assert "PRECEDENCE" in ratio_head, (
        "RATIO CLAIMS section is missing the PRECEDENCE rule at the top "
        "— same flip risk in the reverse direction."
    )


def test_available_tools_catalog_has_runtime_markers(core_prompt: str) -> None:
    """Step 2.6 lock: the AVAILABLE TOOLS catalog must be wrapped in the
    boundary markers PromptBuilder._render_tool_catalog looks for. If
    these markers vanish the catalog stops being filtered against the
    actual tool registry and silently re-diverges from MCP changes."""
    assert "<!-- AVAILABLE_TOOLS_CATALOG_START -->" in core_prompt
    assert "<!-- AVAILABLE_TOOLS_CATALOG_END -->" in core_prompt
    # And the catalog itself must still live between them.
    start = core_prompt.find("<!-- AVAILABLE_TOOLS_CATALOG_START -->")
    end = core_prompt.find("<!-- AVAILABLE_TOOLS_CATALOG_END -->")
    assert start < end
    assert "AVAILABLE TOOLS" in core_prompt[start:end]


def test_agent_tool_scope_appendix_is_declarative() -> None:
    """Step 2.3 lock: agent.py's tool-scope appendix must NOT threaten a
    'fatal error'. The filter at agent.py:212 strips disallowed tools
    before the model sees them, so the threat is false; using declarative
    whitelist wording avoids surprising the model when it tries a tool
    name that is technically valid but not attached this run."""
    from pathlib import Path

    agent_path = Path(__file__).resolve().parent.parent / "mcp_client" / "agent.py"
    src = agent_path.read_text(encoding="utf-8")
    assert "fatal error" not in src.lower(), (
        "agent.py still threatens 'fatal error' for disallowed tools. "
        "The threat is false (the filter strips them) and degrades the "
        "model's trust in the prompt's other claims."
    )
    assert "TOOL SCOPE:" in src, (
        "agent.py no longer carries the TOOL SCOPE appendix. It is what "
        "tells the model which subset of the catalog is in scope this "
        "request when a planner-level tool restriction applies."
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
