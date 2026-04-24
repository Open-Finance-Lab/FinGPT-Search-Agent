"""Unit tests for ``axioms.wrapper.wrap_claim_values``.

Covers candidate generation per ratio, delimited-region preservation,
first-match semantics, idempotency, and structured logging on no-match.
"""

import logging

import pytest

from axioms.wrapper import wrap_claim_values


# ── fixtures ────────────────────────────────────────────────────────


def _claim(ratio, ticker, period, value, claim_id=None):
    return {
        "claim_id": claim_id or f"{ratio}-{ticker}-{period}-0",
        "ratio": ratio,
        "ticker": ticker,
        "period": period,
        "claimed_value": value,
    }


# ── happy paths (three demo ratios) ──────────────────────────────────


def test_gross_margin_wraps_percentage_form():
    prose = "Apple's gross margin was 44.13% in FY2023."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert '<span data-claim-id="gross_margin-AAPL-2023-09-30-0">44.13%</span>' in out
    assert out.replace(
        '<span data-claim-id="gross_margin-AAPL-2023-09-30-0">44.13%</span>',
        "44.13%",
    ) == prose


def test_current_ratio_wraps_decimal_form():
    prose = "Microsoft's current ratio was 0.99 at quarter-end."
    claims = [_claim("current_ratio", "MSFT", "2023-06-30", 0.988)]
    out = wrap_claim_values(prose, claims)
    assert '<span data-claim-id="current_ratio-MSFT-2023-06-30-0">0.99</span>' in out


def test_accounting_equation_wraps_integer_form():
    prose = "Tesla reported total assets of 352,755,000,000 for FY2023."
    claims = [_claim("accounting_equation", "TSLA", "2023-12-31", 352755000000)]
    out = wrap_claim_values(prose, claims)
    assert (
        '<span data-claim-id="accounting_equation-TSLA-2023-12-31-0">352,755,000,000</span>'
        in out
    )


# ── rounding drift ───────────────────────────────────────────────────


def test_gross_margin_rounding_drift_to_one_decimal():
    # Tool call stored 44.13, prose rounds to 44.1%.
    prose = "Gross margin hit 44.1% last quarter."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert '<span data-claim-id="gross_margin-AAPL-2023-09-30-0">44.1%</span>' in out


def test_accounting_equation_billions_suffix():
    # Tool call stored 352755000000, prose says "$352.8 billion".
    prose = "Total assets were $352.8 billion at year-end."
    claims = [_claim("accounting_equation", "TSLA", "2023-12-31", 352755000000)]
    out = wrap_claim_values(prose, claims)
    assert (
        '<span data-claim-id="accounting_equation-TSLA-2023-12-31-0">$352.8 billion</span>'
        in out
    )


def test_accounting_equation_millions_suffix():
    prose = "Total assets equaled $352,755 million."
    claims = [_claim("accounting_equation", "TSLA", "2023-12-31", 352755000000)]
    out = wrap_claim_values(prose, claims)
    assert 'data-claim-id="accounting_equation-TSLA-2023-12-31-0"' in out
    assert "$352,755 million" in out


# ── delimited-region skips (one per kind) ────────────────────────────


def test_skip_inside_fenced_code_block():
    prose = "```\nmargin = 44.13\n```"
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert out == prose  # unchanged — claim falls through to no-match


def test_skip_inside_inline_code():
    prose = "Consider `44.13` as a constant."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert out == prose


def test_skip_inside_inline_math_dollars():
    prose = "The identity $44.13$ appears."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert out == prose


def test_skip_inside_display_math_dollars():
    prose = "$$\ngross\\_margin = 44.13\n$$"
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert out == prose


def test_skip_inside_display_math_brackets():
    prose = r"\[ gm = 44.13 \]"
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert out == prose


def test_skip_inside_inline_math_parens():
    prose = r"See \( 44.13 \) above."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert out == prose


def test_skip_inside_html_attribute():
    prose = '<a href="https://ex.com/44.13/row">row</a>'
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert out == prose


def test_value_in_both_code_and_free_text_only_wraps_free_text():
    prose = "In the snippet ```\n44.13\n``` and also 44.13 in prose."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    # Fenced region preserved verbatim
    assert "```\n44.13\n```" in out
    # Free-text occurrence wrapped
    assert '<span data-claim-id="gross_margin-AAPL-2023-09-30-0">44.13</span> in prose' in out


# ── multiple-occurrence: first match only ────────────────────────────


def test_multiple_occurrence_wraps_first_only():
    prose = "Gross margin of 44.13% this year, up from 44.13% last year."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    # First occurrence wrapped
    assert out.count('<span data-claim-id="gross_margin-AAPL-2023-09-30-0">') == 1
    assert out.startswith("Gross margin of <span")
    # Second occurrence intact, no wrap
    assert out.endswith("up from 44.13% last year.")


# ── no-match case ────────────────────────────────────────────────────


def test_no_match_returns_prose_unchanged_and_logs(caplog):
    prose = "The report contained no relevant figures."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    with caplog.at_level(logging.WARNING, logger="axioms.wrapper"):
        out = wrap_claim_values(prose, claims, session_id="sess-xyz")
    assert out == prose
    assert any(
        "no candidate matched" in record.message for record in caplog.records
    )


# ── already-wrapped: idempotent ──────────────────────────────────────


def test_does_not_double_wrap_if_span_already_present():
    claim = _claim("gross_margin", "AAPL", "2023-09-30", 44.13)
    prose = (
        'Gross margin was <span data-claim-id="gross_margin-AAPL-2023-09-30-0">44.13%</span> '
        "this year."
    )
    out = wrap_claim_values(prose, [claim])
    assert out == prose
    assert out.count('data-claim-id="gross_margin-AAPL-2023-09-30-0"') == 1


# ── multiple claims in one prose ─────────────────────────────────────


def test_multiple_claims_each_wrapped_independently():
    prose = (
        "Apple gross margin 44.13%, Microsoft current ratio 0.99, "
        "Tesla total assets 352,755,000,000."
    )
    claims = [
        _claim("gross_margin", "AAPL", "2023-09-30", 44.13, "gm-0"),
        _claim("current_ratio", "MSFT", "2023-06-30", 0.988, "cr-0"),
        _claim("accounting_equation", "TSLA", "2023-12-31", 352755000000, "ae-0"),
    ]
    out = wrap_claim_values(prose, claims)
    assert '<span data-claim-id="gm-0">44.13%</span>' in out
    assert '<span data-claim-id="cr-0">0.99</span>' in out
    assert '<span data-claim-id="ae-0">352,755,000,000</span>' in out


# ── empty / defensive paths ──────────────────────────────────────────


def test_empty_prose_passes_through():
    assert wrap_claim_values("", [_claim("gross_margin", "AAPL", "2023", 44.13)]) == ""


def test_empty_claims_passes_through():
    prose = "The quick brown fox."
    assert wrap_claim_values(prose, []) == prose


def test_claim_without_claim_id_is_skipped():
    prose = "Gross margin was 44.13%."
    claim = {
        "ratio": "gross_margin",
        "ticker": "AAPL",
        "period": "2023",
        "claimed_value": 44.13,
    }  # no claim_id
    out = wrap_claim_values(prose, [claim])
    assert out == prose


# ── regex: bare '<' comparisons must not swallow the whole tail ──────


def test_literal_less_than_does_not_eat_later_content():
    # "<$100M" is not an HTML tag; the wrapper must still find 44.13%
    # further along in free text rather than treat everything from '<'
    # onwards as one big delimited region.
    prose = "Revenue was <$100M; gross margin held at 44.13% for FY2023."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert '<span data-claim-id="gross_margin-AAPL-2023-09-30-0">44.13%</span>' in out
    # And the original '<$100M' is preserved verbatim.
    assert "<$100M;" in out


def test_angle_bracket_without_tag_name_is_not_delimited():
    # '<5%' and 'x<y' shouldn't register as delimiters either.
    prose = "Threshold x<y triggers review; margin was 44.13% regardless."
    claims = [_claim("gross_margin", "AAPL", "2023-09-30", 44.13)]
    out = wrap_claim_values(prose, claims)
    assert "44.13%</span>" in out
    assert "x<y triggers" in out
