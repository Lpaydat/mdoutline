"""Tests for mdoutline module."""

import mdoutline


def test_backtick_fence_suppresses_headings():
    """Backtick fenced code blocks suppress headings inside them."""
    lines = [
        "# Outside heading",
        "```",
        "# Inside fence - not a heading",
        "## Also not a heading",
        "```",
        "# After fence - is a heading",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Outside heading"), (1, "After fence - is a heading")]


def test_tilde_fence_suppresses_headings():
    """Tilde fenced code blocks suppress headings inside them."""
    lines = [
        "# Outside heading",
        "~~~",
        "# Inside tilde fence - not a heading",
        "~~~",
        "# After fence - is a heading",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Outside heading"), (1, "After fence - is a heading")]


def test_indented_fence_opener_with_backticks():
    """Fence openers with up to 3 leading spaces still open fences."""
    lines = [
        "# Before",
        "   ```",
        "# Inside indented fence",
        "   ```",
        "# After",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Before"), (1, "After")]


def test_indented_fence_opener_with_tildes():
    """Tilde fence openers with up to 3 leading spaces still open fences."""
    lines = [
        "# Before",
        "  ~~~",
        "# Inside indented tilde fence",
        "  ~~~",
        "# After",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Before"), (1, "After")]


def test_four_leading_spaces_does_not_open_fence():
    """Four leading spaces means the line is not a fence opener."""
    lines = [
        "# Before",
        "    ```",
        "# This should be a heading (4 spaces doesn't open fence)",
        "    ```",
        "# After",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [
        (1, "Before"),
        (1, "This should be a heading (4 spaces doesn't open fence)"),
        (1, "After"),
    ]


def test_unclosed_fence_at_eof_suppresses_to_end():
    """Unclosed fence suppresses all headings until EOF."""
    lines = [
        "# Before fence",
        "```",
        "# Inside unclosed fence",
        "## Also inside",
        "### Still inside",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Before fence")]


def test_unclosed_tilde_fence_at_eof():
    """Unclosed tilde fence suppresses all headings until EOF."""
    lines = [
        "# Before",
        "~~~",
        "# Inside",
        "## More inside",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Before")]


def test_depth_boundaries_1_to_6_recognized():
    """Depths 1-6 are recognized as headings."""
    lines = [
        "# H1",
        "## H2",
        "### H3",
        "#### H4",
        "##### H5",
        "###### H6",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [
        (1, "H1"),
        (2, "H2"),
        (3, "H3"),
        (4, "H4"),
        (5, "H5"),
        (6, "H6"),
    ]


def test_seven_or_more_hashes_not_a_heading():
    """Seven or more consecutive hashes are not recognized as a heading."""
    lines = [
        "# Valid",
        "####### Not valid - 7 hashes",
        "## Also valid",
        "######## Also not valid - 8 hashes",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Valid"), (2, "Also valid")]


def test_three_or_fewer_leading_spaces_is_heading():
    """Headings with up to 3 leading spaces are recognized."""
    lines = [
        "# No indent",
        " # One space",
        "  # Two spaces",
        "   # Three spaces",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [
        (1, "No indent"),
        (1, "One space"),
        (1, "Two spaces"),
        (1, "Three spaces"),
    ]


def test_four_or_more_leading_spaces_not_a_heading():
    """Lines with 4+ leading spaces are not headings."""
    lines = [
        "# Valid",
        "    # Four spaces - not a heading",
        "     # Five spaces - not a heading",
        "## Also valid",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Valid"), (2, "Also valid")]


def test_hash_without_space_not_a_heading():
    """Hashes without a following space are not headings."""
    lines = [
        "# Valid heading",
        "#notvalid - no space after hash",
        "## Valid too",
        "###also not valid",
        "#### Still valid",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Valid heading"), (2, "Valid too"), (4, "Still valid")]


def test_trailing_closing_hashes_stripped():
    """Trailing closing hashes with optional whitespace are stripped."""
    lines = [
        "## Title ##",
        "### Header ###",
        "#### Section ####",
        "##### Heading #####",
        "###### Subsection ######",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [
        (2, "Title"),
        (3, "Header"),
        (4, "Section"),
        (5, "Heading"),
        (6, "Subsection"),
    ]


def test_trailing_hashes_with_whitespace_stripped():
    """Trailing hashes with whitespace before them are stripped."""
    lines = [
        "## Title   ##",
        "### Header     ###",
        "#### Section\t####",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(2, "Title"), (3, "Header"), (4, "Section")]


def test_hash_alone_yields_empty_text():
    """A single # with no text yields depth 1, empty string."""
    lines = [
        "#",
        "##",
        "###",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, ""), (2, ""), (3, "")]


def test_whitespace_tolerance_text_stripped():
    """Heading text is stripped of leading/trailing whitespace."""
    lines = [
        "#   Title with spaces   ",
        "##  Another header  ",
        "###   No leading/trailing spaces   ",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [
        (1, "Title with spaces"),
        (2, "Another header"),
        (3, "No leading/trailing spaces"),
    ]


def test_empty_input_returns_no_headings():
    """Empty input returns empty list."""
    result = mdoutline.extract_headings([])
    assert result == []


def test_no_headings_in_input():
    """Input with no heading lines returns empty list."""
    lines = [
        "Just some text",
        "More text",
        "Even more text",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == []


def test_generator_input():
    """extract_headings works with generator input."""

    def line_generator():
        yield "# First"
        yield "## Second"
        yield "### Third"

    result = mdoutline.extract_headings(line_generator())
    assert result == [(1, "First"), (2, "Second"), (3, "Third")]


def test_render_h1_at_column_zero():
    """H1 headings render at column 0."""
    headings = [(1, "Title"), (1, "Another")]
    result = mdoutline.render_outline(headings)
    assert result == "- Title\n- Another\n"


def test_render_nested_depths_with_two_space_indents():
    """Nested headings use 2-space indents per depth level."""
    headings = [
        (1, "Level 1"),
        (2, "Level 2"),
        (3, "Level 3"),
        (4, "Level 4"),
        (5, "Level 5"),
        (6, "Level 6"),
    ]
    result = mdoutline.render_outline(headings)
    expected = (
        "- Level 1\n"
        "  - Level 2\n"
        "    - Level 3\n"
        "      - Level 4\n"
        "        - Level 5\n"
        "          - Level 6\n"
    )
    assert result == expected


def test_render_empty_list_returns_empty_string():
    """Empty input list returns empty string (no newline)."""
    result = mdoutline.render_outline([])
    assert result == ""


def test_render_no_trailing_whitespace():
    """Rendered output has no trailing whitespace on lines."""
    headings = [(1, "Title"), (2, "Sub")]
    result = mdoutline.render_outline(headings)
    lines = result.split("\n")
    # Last line is empty due to trailing newline, check others
    for line in lines[:-1]:
        assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"


def test_render_ends_with_single_newline():
    """Non-empty output ends with exactly one trailing newline."""
    headings = [(1, "Title")]
    result = mdoutline.render_outline(headings)
    assert result.endswith("\n")
    assert not result.endswith("\n\n")


def test_render_empty_text_no_trailing_space():
    """Heading with empty text renders as dash only (no trailing space)."""
    headings = [(1, "")]
    result = mdoutline.render_outline(headings)
    assert result == "-\n"


def test_render_mixed_empty_and_nonempty_text():
    """Mixed empty and non-empty heading texts render correctly."""
    headings = [(1, ""), (2, "x")]
    result = mdoutline.render_outline(headings)
    assert result == "-\n  - x\n"


def test_different_fence_chars_do_not_close():
    """Different fence characters do not close a fence."""
    lines = [
        "# Before",
        "```",
        "# Inside backtick fence",
        "~~~",
        "# This is still inside (tilde doesn't close backtick)",
        "```",
        "# After backtick closes",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Before"), (1, "After backtick closes")]


def test_fence_closing_requires_same_char():
    """Fence closing requires the same character that opened it."""
    lines = [
        "# Before",
        "~~~",
        "# Inside tilde fence",
        "```",
        "# Still inside (backtick doesn't close tilde)",
        "~~~",
        "# After tilde closes",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Before"), (1, "After tilde closes")]


def test_fence_closing_behavior():
    """Fence lines of the same character close the current fence."""
    lines = [
        "# Before first fence",
        "```",
        "# Inside first fence",
        "```",
        "# Between fences - is a heading",
        "```",
        "# Inside second fence",
        "```",
        "# After second fence - is a heading",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [
        (1, "Before first fence"),
        (1, "Between fences - is a heading"),
        (1, "After second fence - is a heading"),
    ]


def test_heading_with_internal_hashes():
    """Hashes within the heading text are preserved."""
    lines = [
        "# Chapter #1: Introduction",
        "## Section #2",
        "### Heading #3 #",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [
        (1, "Chapter #1: Introduction"),
        (2, "Section #2"),
        (3, "Heading #3"),
    ]


def test_minimal_fence_opener():
    """Three fence characters is the minimum to open a fence."""
    lines = [
        "# Before",
        "```",
        "# Inside",
        "```",
        "# After",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Before"), (1, "After")]


def test_two_backticks_not_a_fence():
    """Two backticks do not open a fence."""
    lines = [
        "# Before",
        "``",
        "# This is a heading (not a fence)",
        "``",
        "# After",
    ]
    result = mdoutline.extract_headings(lines)
    assert result == [(1, "Before"), (1, "This is a heading (not a fence)"), (1, "After")]


def test_extract_and_render_integration():
    """Integration test: extract and render a complete outline."""
    lines = [
        "# Document Title",
        "## Introduction",
        "### Background",
        "### Motivation",
        "## Methods",
        "### Data Collection",
        "### Analysis",
        "## Results",
        "## Discussion",
        "## Conclusion",
    ]
    headings = mdoutline.extract_headings(lines)
    outline = mdoutline.render_outline(headings)
    expected = (
        "- Document Title\n"
        "  - Introduction\n"
        "    - Background\n"
        "    - Motivation\n"
        "  - Methods\n"
        "    - Data Collection\n"
        "    - Analysis\n"
        "  - Results\n"
        "  - Discussion\n"
        "  - Conclusion\n"
    )
    assert outline == expected
