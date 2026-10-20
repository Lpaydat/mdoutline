"""Tests for newline-only splitting (Item 7u7)."""


def test_u2028_line_separator_not_split(tmp_path, run_cli):
    """U+2028 must NOT split lines (phantom heading)."""
    test_file = tmp_path / "test.md"
    # U+2028 is Unicode LINE SEPARATOR
    test_file.write_text("Intro: cost\u2028## Fake heading\n", encoding="utf-8")
    result = run_cli([str(test_file)])
    assert result.returncode == 0
    assert result.stdout == ""


def test_u0085_next_line_not_split(tmp_path, run_cli):
    """U+0085 must NOT split lines."""
    test_file = tmp_path / "test.md"
    test_file.write_text("Intro: cost\u0085## Fake heading\n", encoding="utf-8")
    result = run_cli([str(test_file)])
    assert result.returncode == 0
    assert result.stdout == ""


def test_form_feed_not_split(tmp_path, run_cli):
    """\\x0c (form feed) must NOT split lines."""
    test_file = tmp_path / "test.md"
    test_file.write_text("Intro: cost\x0c## Fake heading\n", encoding="utf-8")
    result = run_cli([str(test_file)])
    assert result.returncode == 0
    assert result.stdout == ""


def test_file_separator_not_split(tmp_path, run_cli):
    """\\x1c (file separator) must NOT split lines."""
    test_file = tmp_path / "test.md"
    test_file.write_text("Intro: cost\x1c## Fake heading\n", encoding="utf-8")
    result = run_cli([str(test_file)])
    assert result.returncode == 0
    assert result.stdout == ""


def test_group_separator_not_split(tmp_path, run_cli):
    """\\x1d (group separator) must NOT split lines."""
    test_file = tmp_path / "test.md"
    test_file.write_text("Intro: cost\x1d## Fake heading\n", encoding="utf-8")
    result = run_cli([str(test_file)])
    assert result.returncode == 0
    assert result.stdout == ""


def test_record_separator_not_split(tmp_path, run_cli):
    """\\x1e (record separator) must NOT split lines."""
    test_file = tmp_path / "test.md"
    test_file.write_text("Intro: cost\x1e## Fake heading\n", encoding="utf-8")
    result = run_cli([str(test_file)])
    assert result.returncode == 0
    assert result.stdout == ""


def test_crlf_split_correctly(tmp_path, run_cli):
    """CRLF line endings should split correctly."""
    test_file = tmp_path / "test.md"
    # Write with CRLF
    with open(test_file, "wb") as f:
        f.write(b"# Hi\r\n## Sub\r\n")
    result = run_cli([str(test_file)])
    assert result.returncode == 0
    assert result.stdout == "- Hi\n  - Sub\n"


def test_lone_cr_split_correctly(tmp_path, run_cli):
    """Lone CR should be treated like LF."""
    test_file = tmp_path / "test.md"
    # Write with lone CR
    with open(test_file, "wb") as f:
        f.write(b"# A\r# B")
    result = run_cli([str(test_file)])
    assert result.returncode == 0
    assert result.stdout == "- A\n- B\n"
