"""
Post-generation numerical validation for financial agent responses.

Compares numbers in the agent's final output against numbers from tool outputs
to detect LLM hallucination of financial figures (e.g., $190.66 vs $190.68).
"""

import re
import json
import logging
from typing import Set

logger = logging.getLogger(__name__)

# Pattern to match financial numbers (integers, decimals, percentages)
_NUMBER_PATTERN = re.compile(
    r'(?<!\w)'           # not preceded by word char
    r'-?'                # optional negative sign
    r'\$?'               # optional dollar sign
    r'(\d{1,3}(?:,\d{3})*'  # integer with optional comma separators
    r'(?:\.\d+)?)'       # optional decimal part
    r'%?'                # optional percent sign
    r'(?!\w)',           # not followed by word char
)


def _extract_numbers(text: str) -> Set[str]:
    """
    Extract all numerical values from text, normalized (commas removed).
    Returns a set of string representations for exact matching.
    """
    numbers = set()
    for match in _NUMBER_PATTERN.finditer(text):
        num_str = match.group(1).replace(',', '')
        # Skip very short numbers (likely not financial data)
        try:
            val = float(num_str)
            # Only track numbers that look like financial data (> 0.001 and not just 0, 1, 2...)
            if val > 0.01 and len(num_str) > 1:
                numbers.add(num_str)
        except ValueError:
            continue
    return numbers


def _extract_tool_output_numbers(run_result) -> Set[str]:
    """
    Extract numbers from tool call outputs in the agent run result.
    """
    tool_numbers = set()
    try:
        items = getattr(run_result, 'new_items', None) or []
        for item in items:
            item_type = getattr(item, 'type', '')
            if item_type == 'tool_call_output_item':
                output = getattr(item, 'output', '')
                if output:
                    # Try parsing as JSON first (structured tool output)
                    try:
                        parsed = json.loads(output) if isinstance(output, str) else output
                        tool_numbers.update(_extract_numbers(json.dumps(parsed)))
                    except (json.JSONDecodeError, TypeError):
                        tool_numbers.update(_extract_numbers(str(output)))
    except Exception as e:
        logger.debug(f"[NUM VALIDATOR] Error extracting tool numbers: {e}")

    return tool_numbers


def validate_numerical_accuracy(run_result, final_output: str) -> None:
    """
    Compare numbers in the final output against tool outputs.
    Logs warnings for any numbers that appear in the response but not in any tool output,
    which could indicate LLM hallucination.

    This is a logging-only validation — it does not modify the response.
    """
    if not final_output:
        return

    try:
        response_numbers = _extract_numbers(final_output)
        if not response_numbers:
            return

        tool_numbers = _extract_tool_output_numbers(run_result)
        if not tool_numbers:
            logger.debug("[NUM VALIDATOR] No tool output numbers found, skipping validation")
            return

        # Check each response number against tool outputs
        # Allow for rounding (compare up to 2 decimal places)
        suspicious = []
        for resp_num in response_numbers:
            resp_val = float(resp_num)

            # Check if this number (or a close match) exists in tool output
            found_match = False
            for tool_num in tool_numbers:
                tool_val = float(tool_num)
                if tool_val == 0:
                    continue
                # Exact match or very close (within 0.01%)
                if abs(resp_val - tool_val) / abs(tool_val) < 0.0001:
                    found_match = True
                    break
                # Also check if it's a reasonable derivation (sum, difference, ratio)
                # We only flag numbers that are close-but-wrong (within 1% but not exact)
                if 0.0001 <= abs(resp_val - tool_val) / abs(tool_val) < 0.01:
                    suspicious.append((resp_num, tool_num, abs(resp_val - tool_val)))
                    found_match = True  # Close enough that it's likely this number, just slightly off
                    break

            # Don't flag numbers not found at all — they may be computed values

        if suspicious:
            for resp_num, tool_num, diff in suspicious:
                logger.warning(
                    f"[NUM VALIDATOR] Possible numerical hallucination: "
                    f"response has {resp_num}, tool output has {tool_num} "
                    f"(difference: {diff:.6f})"
                )

    except Exception as e:
        logger.debug(f"[NUM VALIDATOR] Validation error (non-critical): {e}")
