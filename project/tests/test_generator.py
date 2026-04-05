"""Tests for generator.py: _parse_sections logic."""

from glass.generator import _parse_sections


def test_parse_sections_both_tags():
    """Both <reasoning> and <answer> tags present."""
    text = """<reasoning>
Step 1: Consider the question.
Step 2: Evaluate evidence.
</reasoning>

<answer>
The answer is 42.
</answer>"""
    answer, reasoning = _parse_sections(text)
    assert "42" in answer
    assert "Step 1" in reasoning
    assert "Step 2" in reasoning
    # Tags themselves should not be in the output
    assert "<reasoning>" not in reasoning
    assert "<answer>" not in answer


def test_parse_sections_no_tags():
    """No tags present — answer should be the full text, reasoning empty."""
    text = "This is a plain response with no XML tags at all."
    answer, reasoning = _parse_sections(text)
    assert answer == text
    assert reasoning == ""


def test_parse_sections_only_reasoning():
    """Only <reasoning> tags, no <answer> — answer is the full text."""
    text = """<reasoning>
Some thought process here.
</reasoning>

The answer without tags."""
    answer, reasoning = _parse_sections(text)
    assert "Some thought process" in reasoning
    # Without answer tags, the full text becomes the answer
    assert answer == text


def test_parse_sections_answer_without_closing():
    """<answer> tag present but no closing tag — takes everything after."""
    text = """<reasoning>
Thinking...
</reasoning>

<answer>
The final answer is here and continues to the end."""
    answer, reasoning = _parse_sections(text)
    assert "final answer" in answer
    assert "Thinking" in reasoning


def test_parse_sections_empty_string():
    """Empty string input."""
    answer, reasoning = _parse_sections("")
    assert answer == ""
    assert reasoning == ""
