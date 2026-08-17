"""Fence behavior tests for CommonMark compliance."""

from mdoutline import extract_headings


def test_fence_info_string_not_a_closer():
    """D1: Fence with info string is content, not a closer.

    CommonMark: a closing fence may not carry an info string.
    '```python' does NOT close a fence opened with '```'.
    """
    lines = ["# Doc", "```", "```python", "# comment inside example", "```", "# After"]
    result = extract_headings(lines)
    assert result == [(1, "Doc"), (1, "After")]


def test_fence_closer_must_match_opener_length():
    """D2: Closing fence must be at least as long as the opener.

    CommonMark: closing fence must be >= opener length.
    A 3-backtick fence does NOT close a 4-backtick opener.
    """
    lines = ["# Doc", "````", "# inner", "```", "# still inner per CommonMark", "````", "# After"]
    result = extract_headings(lines)
    assert result == [(1, "Doc"), (1, "After")]


def test_longer_closer_closes_fence():
    """A 3-backtick opener is closed by a 4-backtick closer."""
    lines = ["# Doc", "```", "# inside", "````", "# After"]
    result = extract_headings(lines)
    assert result == [(1, "Doc"), (1, "After")]


def test_tilde_fence_info_string_not_a_closer():
    """Tilde fence with info string is content, not a closer."""
    lines = ["# Doc", "~~~", "~~~python", "# comment inside example", "~~~", "# After"]
    result = extract_headings(lines)
    assert result == [(1, "Doc"), (1, "After")]


def test_tilde_fence_closer_must_match_opener_length():
    """Tilde fence closer must be at least as long as the opener."""
    lines = ["# Doc", "~~~~", "# inner", "~~~", "# still inner per CommonMark", "~~~~", "# After"]
    result = extract_headings(lines)
    assert result == [(1, "Doc"), (1, "After")]


def test_fence_closer_no_trailing_content():
    """A closer with non-space trailing content is not a closer."""
    lines = ["# Doc", "```", "# inside", "```x", "# still inside", "```", "# After"]
    result = extract_headings(lines)
    assert result == [(1, "Doc"), (1, "After")]


def test_fence_with_leading_spaces_closes():
    """A closer with <=3 leading spaces can close a fence."""
    lines = ["# Doc", "```", "# inside", "   ```", "# After"]
    result = extract_headings(lines)
    assert result == [(1, "Doc"), (1, "After")]


def test_fence_with_four_leading_spaces_does_not_close():
    """A closer with 4+ leading spaces does NOT close a fence."""
    lines = ["# Doc", "```", "# inside", "    ```", "# still inside", "```", "# After"]
    result = extract_headings(lines)
    assert result == [(1, "Doc"), (1, "After")]
