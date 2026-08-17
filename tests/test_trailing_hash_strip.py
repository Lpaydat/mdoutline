"""Trailing hash stripping tests per CommonMark spec."""

from mdoutline import extract_headings


def test_trailing_hash_preceded_by_space():
    """'## Title ##' -> 'Title' (space before closing #s)"""
    lines = ["## Title ##"]
    assert extract_headings(lines) == [(2, "Title")]


def test_trailing_hash_preceded_by_tab():
    """'# foo \t#' -> 'foo' (tab before closing #s)"""
    lines = ["# foo \t#"]
    assert extract_headings(lines) == [(1, "foo")]


def test_trailing_hash_without_space_not_stripped():
    """'## C#' -> (2, 'C#') (no space before #, keep it)"""
    lines = ["## C#"]
    assert extract_headings(lines) == [(2, "C#")]


def test_trailing_hash_without_space_not_stripped_foo():
    """'# foo#' -> (1, 'foo#')"""
    lines = ["# foo#"]
    assert extract_headings(lines) == [(1, "foo#")]


def test_trailing_hash_without_space_not_stripped_double():
    """'## T##' -> (2, 'T##')"""
    lines = ["## T##"]
    assert extract_headings(lines) == [(2, "T##")]


def test_trailing_hash_with_bar_not_stripped():
    """'# foo# bar' -> 'foo# bar' (# not at end)"""
    lines = ["# foo# bar"]
    assert extract_headings(lines) == [(1, "foo# bar")]


def test_trailing_hashes_only():
    """'## ##' -> '' (space then #s, entire text after space)"""
    lines = ["## ##"]
    assert extract_headings(lines) == [(2, "")]


def test_trailing_hashes_only_single():
    """'# ###' -> ''"""
    lines = ["# ###"]
    assert extract_headings(lines) == [(1, "")]


def test_space_separated_trailing_hashes():
    """'# Title #' -> 'Title' (space before closing #s)"""
    lines = ["# Title #"]
    assert extract_headings(lines) == [(1, "Title")]


def test_multiple_trailing_hashes_with_space():
    """'### Section ###' -> 'Section'"""
    lines = ["### Section ###"]
    assert extract_headings(lines) == [(3, "Section")]
