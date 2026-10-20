"""Tests for mdoutline module."""

import pytest

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


def test_filter_by_depth_keeps_shallow_headings():
    """filter_by_depth keeps headings with depth <= max_depth."""
    headings = [(1, "H1"), (2, "H2"), (3, "H3"), (4, "H4")]
    result = mdoutline.filter_by_depth(headings, 2)
    assert result == [(1, "H1"), (2, "H2")]


def test_filter_by_depth_drops_deeper_headings():
    """filter_by_depth drops headings deeper than max_depth."""
    headings = [(1, "One"), (2, "Two"), (3, "Three"), (4, "Four")]
    result = mdoutline.filter_by_depth(headings, 1)
    assert result == [(1, "One")]


def test_filter_by_depth_none_returns_all():
    """filter_by_depth with max_depth=None returns all headings unchanged."""
    headings = [(1, "A"), (2, "B"), (3, "C")]
    result = mdoutline.filter_by_depth(headings, None)
    assert result == [(1, "A"), (2, "B"), (3, "C")]


def test_filter_by_depth_preserves_order():
    """filter_by_depth preserves the original order of headings."""
    headings = [(3, "Deep"), (1, "Shallow"), (2, "Medium"), (4, "Deepest")]
    result = mdoutline.filter_by_depth(headings, 2)
    assert result == [(1, "Shallow"), (2, "Medium")]


def test_filter_by_depth_preserves_depth_values():
    """filter_by_depth does not re-level depth values."""
    headings = [(1, "H1"), (3, "H3")]
    result = mdoutline.filter_by_depth(headings, 3)
    # H3 should keep depth 3, not be re-leveled to 2
    assert result == [(1, "H1"), (3, "H3")]


def test_filter_by_depth_empty_input():
    """filter_by_depth with empty input returns empty list."""
    result = mdoutline.filter_by_depth([], 2)
    assert result == []


def test_filter_by_depth_max_depth_one_only_h1():
    """filter_by_depth with max_depth=1 keeps only h1 headings."""
    headings = [(1, "Title"), (2, "Section"), (1, "Another"), (3, "Sub")]
    result = mdoutline.filter_by_depth(headings, 1)
    assert result == [(1, "Title"), (1, "Another")]


def test_filter_by_depth_max_depth_greater_than_deepest():
    """filter_by_depth with max_depth >= deepest keeps everything."""
    headings = [(1, "A"), (2, "B"), (3, "C")]
    result = mdoutline.filter_by_depth(headings, 10)
    assert result == [(1, "A"), (2, "B"), (3, "C")]


def test_filter_by_depth_max_depth_equals_deepest():
    """filter_by_depth with max_depth equal to deepest keeps everything."""
    headings = [(1, "A"), (2, "B"), (4, "D")]
    result = mdoutline.filter_by_depth(headings, 4)
    assert result == [(1, "A"), (2, "B"), (4, "D")]


def test_filter_by_depth_does_not_mutate_input():
    """filter_by_depth does not mutate the input list."""
    headings = [(1, "A"), (2, "B"), (3, "C")]
    original = headings.copy()
    mdoutline.filter_by_depth(headings, 2)
    assert headings == original


def test_filter_by_depth_returns_new_list():
    """filter_by_depth returns a new list, not the input."""
    headings = [(1, "A"), (2, "B")]
    result = mdoutline.filter_by_depth(headings, 1)
    assert result is not headings


def test_filter_by_depth_none_returns_copy():
    """filter_by_depth with max_depth=None returns a copy of the input."""
    headings = [(1, "A"), (2, "B")]
    result = mdoutline.filter_by_depth(headings, None)
    assert result == headings
    assert result is not headings


def test_filter_by_depth_boundary_values():
    """filter_by_depth works at depth boundaries."""
    headings = [(1, "H1"), (2, "H2"), (3, "H3"), (4, "H4"), (5, "H5"), (6, "H6")]
    result = mdoutline.filter_by_depth(headings, 3)
    assert result == [(1, "H1"), (2, "H2"), (3, "H3")]


def test_filter_by_depth_all_deeper_than_max():
    """filter_by_depth returns empty list when all headings are deeper."""
    headings = [(2, "H2"), (3, "H3"), (4, "H4")]
    result = mdoutline.filter_by_depth(headings, 1)
    assert result == []


def test_filter_by_depth_all_shallow_or_equal():
    """filter_by_depth keeps all when all are at or below max_depth."""
    headings = [(1, "H1"), (1, "Another H1"), (2, "H2")]
    result = mdoutline.filter_by_depth(headings, 2)
    assert result == [(1, "H1"), (1, "Another H1"), (2, "H2")]


def test_number_headings_canonical_vector():
    """Canonical test vector: h1 A, h2 B, h2 C, h3 D, h2 E, h1 F."""
    headings = [(1, "A"), (2, "B"), (2, "C"), (3, "D"), (2, "E"), (1, "F")]
    result = mdoutline.number_headings(headings)
    expected = [
        (1, "A", "1."),
        (2, "B", "1.1"),
        (2, "C", "1.2"),
        (3, "D", "1.2.1"),
        (2, "E", "1.3"),
        (1, "F", "2."),
    ]
    assert result == expected


def test_number_headings_depth_increments_and_resets_deeper():
    """Depth d increments counter[d] and resets all deeper counters to 0."""
    headings = [(1, "A"), (2, "B"), (3, "C"), (2, "D"), (3, "E")]
    result = mdoutline.number_headings(headings)
    expected = [
        (1, "A", "1."),
        (2, "B", "1.1"),
        (3, "C", "1.1.1"),
        (2, "D", "1.2"),
        (3, "E", "1.2.1"),
    ]
    assert result == expected


def test_number_headings_level_jump_h1_to_h3():
    """Level jump from h1 to h3 produces mechanical 0 for skipped level."""
    headings = [(1, "A"), (3, "B")]
    result = mdoutline.number_headings(headings)
    expected = [(1, "A", "1."), (3, "B", "1.0.1")]
    assert result == expected


def test_number_headings_h3_then_h2_continues_h2_counter():
    """An h3 followed by h2 continues the h2 counter from before."""
    headings = [(1, "A"), (2, "B"), (3, "C"), (2, "D")]
    result = mdoutline.number_headings(headings)
    expected = [(1, "A", "1."), (2, "B", "1.1"), (3, "C", "1.1.1"), (2, "D", "1.2")]
    assert result == expected


def test_number_headings_h2_to_h4_produces_mechanical_zeros():
    """Jump from h2 to h4 produces mechanical zeros for skipped levels."""
    headings = [(1, "A"), (2, "B"), (4, "C")]
    result = mdoutline.number_headings(headings)
    expected = [(1, "A", "1."), (2, "B", "1.1"), (4, "C", "1.1.0.1")]
    assert result == expected


def test_number_headings_depth_1_trailing_dot():
    """Depth 1 headings have trailing dot in their number."""
    headings = [(1, "A"), (1, "B"), (1, "C")]
    result = mdoutline.number_headings(headings)
    assert result == [(1, "A", "1."), (1, "B", "2."), (1, "C", "3.")]


def test_number_headings_depth_2_no_trailing_dot():
    """Depth 2 and deeper headings have no trailing dot."""
    headings = [(1, "A"), (2, "B"), (3, "C")]
    result = mdoutline.number_headings(headings)
    assert result[1][2] == "1.1"  # No trailing dot
    assert result[2][2] == "1.1.1"  # No trailing dot


def test_number_headings_empty_input_returns_empty():
    """Empty input returns empty list."""
    result = mdoutline.number_headings([])
    assert result == []


def test_number_headings_single_h1():
    """Single h1 heading produces ['1.']."""
    headings = [(1, "Title")]
    result = mdoutline.number_headings(headings)
    assert result == [(1, "Title", "1.")]


def test_number_headings_does_not_mutate_input():
    """number_headings does not mutate the input list."""
    headings = [(1, "A"), (2, "B"), (3, "C")]
    original = list(headings)  # Shallow copy is fine for tuples
    mdoutline.number_headings(headings)
    assert headings == original


def test_number_headings_returns_new_list():
    """number_headings returns a new list, not the input."""
    headings = [(1, "A"), (2, "B")]
    result = mdoutline.number_headings(headings)
    assert result is not headings


def test_number_headings_multiple_h1s_increment():
    """Multiple h1 headings each increment the top-level counter."""
    headings = [(1, "A"), (1, "B"), (1, "C"), (1, "D")]
    result = mdoutline.number_headings(headings)
    expected = [(1, "A", "1."), (1, "B", "2."), (1, "C", "3."), (1, "D", "4.")]
    assert result == expected


def test_number_headings_deep_nesting():
    """Deep nesting (up to depth 6) works correctly."""
    headings = [(1, "A"), (2, "B"), (3, "C"), (4, "D"), (5, "E"), (6, "F")]
    result = mdoutline.number_headings(headings)
    expected = [
        (1, "A", "1."),
        (2, "B", "1.1"),
        (3, "C", "1.1.1"),
        (4, "D", "1.1.1.1"),
        (5, "E", "1.1.1.1.1"),
        (6, "F", "1.1.1.1.1.1"),
    ]
    assert result == expected


def test_number_headings_complex_structure():
    """Complex heading structure with multiple level changes."""
    headings = [
        (1, "One"),
        (2, "One.One"),
        (3, "One.One.One"),
        (3, "One.One.Two"),
        (2, "One.Two"),
        (3, "One.Two.One"),
        (1, "Two"),
        (2, "Two.One"),
        (2, "Two.Two"),
    ]
    result = mdoutline.number_headings(headings)
    expected = [
        (1, "One", "1."),
        (2, "One.One", "1.1"),
        (3, "One.One.One", "1.1.1"),
        (3, "One.One.Two", "1.1.2"),
        (2, "One.Two", "1.2"),
        (3, "One.Two.One", "1.2.1"),
        (1, "Two", "2."),
        (2, "Two.One", "2.1"),
        (2, "Two.Two", "2.2"),
    ]
    assert result == expected


def test_number_headings_depth_7_raises_value_error():
    """Depth 7 raises ValueError naming the depth, not a raw IndexError."""
    with pytest.raises(ValueError, match="depth must be 1-6, got 7"):
        mdoutline.number_headings([(7, "x")])


def test_number_headings_depth_0_raises_value_error():
    """Depth 0 raises ValueError naming the depth, not a silent empty number."""
    with pytest.raises(ValueError, match="depth must be 1-6, got 0"):
        mdoutline.number_headings([(0, "zero")])


def test_number_headings_negative_depth_raises_value_error():
    """Negative depth raises ValueError naming the depth, not a silent empty number."""
    with pytest.raises(ValueError, match="depth must be 1-6, got -1"):
        mdoutline.number_headings([(-1, "neg")])
