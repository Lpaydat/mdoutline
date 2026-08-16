"""CLI tests for mdoutline."""


def test_file_argument(tmp_path, run_cli, write_md_file):
    """Test reading from a file argument."""
    test_file = write_md_file(
        "test.md",
        "# Title\n"
        "## Section 1\n"
        "### Subsection 1.1\n"
        "## Section 2\n"
        "### Subsection 2.1\n"
        "#### Sub-subsection 2.1.1\n",
    )

    result = run_cli([str(test_file)])

    expected = (
        "- Title\n"
        "  - Section 1\n"
        "    - Subsection 1.1\n"
        "  - Section 2\n"
        "    - Subsection 2.1\n"
        "      - Sub-subsection 2.1.1\n"
    )
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""


def test_stdin_fallback(run_cli):
    """Test reading from stdin when no file argument is provided."""
    content = "# Title\n## Section 1\n### Subsection 1.1\n## Section 2\n"

    result = run_cli([], stdin=content.encode())

    expected = "- Title\n  - Section 1\n    - Subsection 1.1\n  - Section 2\n"
    assert result.returncode == 0
    assert result.stdout.decode() == expected
    assert result.stderr.decode() == ""


def test_missing_file(run_cli):
    """Test error handling for a missing file."""
    result = run_cli(["NOTES.md"])

    assert result.returncode == 1
    stderr = result.stderr
    assert "NOTES.md" in stderr
    assert "Traceback" not in stderr
    assert stderr != ""


def test_empty_stdin(run_cli):
    """Test empty input from stdin."""
    result = run_cli([], stdin=b"")

    assert result.returncode == 0
    assert result.stdout.decode() == ""
    assert result.stderr.decode() == ""


def test_file_with_no_headings(tmp_path, run_cli, write_md_file):
    """Test a file with no headings."""
    write_md_file("no_headings.md", "Just some text\nMore text\nEven more text\n")

    result = run_cli([str(tmp_path / "no_headings.md")])

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_broken_pipe_no_traceback(run_cli_pipeline):
    """Test broken pipe produces no traceback, and consumer receives content."""
    # Generate a large outline that exceeds pipe buffer (~64KB)
    lines = [f"# Heading {i}\n## Sub {i}\n### Subsub {i}\n" for i in range(5000)]
    content = "".join(lines)

    result = run_cli_pipeline("| head -1", stdin=content)

    stdout = result.stdout
    stderr = result.stderr

    # Should get the first line of output
    assert stdout == "- Heading 0\n"
    # No traceback and no BrokenPipeError message in stderr
    assert "Traceback" not in stderr
    assert "BrokenPipeError" not in stderr
    # The actual exit code from head (0), not the SIGPIPE from mdoutline
    assert result.returncode == 0


def test_bom_file(tmp_path, run_cli, write_md_file):
    """Test UTF-8 BOM is handled correctly for file input."""
    # Write BOM + content (Python's \ufeff encodes to UTF-8 BOM)
    write_md_file("bom.md", "\ufeff# Title\n## Section\n")

    result = run_cli([str(tmp_path / "bom.md")])

    expected = "- Title\n  - Section\n"
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""


def test_bom_stdin(run_cli):
    """Test UTF-8 BOM is handled correctly for stdin input."""
    bom_content = b"\xef\xbb\xbf# Title\n## Section\n"

    result = run_cli([], stdin=bom_content)

    expected = "- Title\n  - Section\n"
    assert result.returncode == 0
    assert result.stdout.decode() == expected
    assert result.stderr.decode() == ""


def test_empty_string_argument(run_cli):
    """Test empty string argument is treated as missing file, not stdin."""
    result = run_cli([""])

    assert result.returncode == 1
    stderr = result.stderr
    # Should contain the error about reading empty filename
    assert "cannot read" in stderr.lower()
    assert "Traceback" not in stderr
    assert stderr != ""


def test_invalid_utf8_stdin(run_cli):
    """Test invalid UTF-8 on stdin produces proper error message."""
    # Invalid UTF-8 bytes
    invalid_utf8 = b"\xff\xfe\x00\x00"

    result = run_cli([], stdin=invalid_utf8)

    assert result.returncode == 1
    stderr = result.stderr.decode()
    # Should name stdin, not 'None'
    assert "stdin" in stderr.lower()
    assert "None" not in stderr
    assert "Traceback" not in stderr
    assert stderr != ""


def test_max_depth_file(tmp_path, run_cli, write_md_file):
    """Test --max-depth limits heading depth in file mode."""
    write_md_file("depth.md", "# H1\n## H2-1\n### H3-1\n#### H4-1\n## H2-2\n### H3-2\n")

    result = run_cli(["--max-depth", "2", str(tmp_path / "depth.md")])

    expected = "- H1\n  - H2-1\n  - H2-2\n"
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""


def test_max_depth_stdin(run_cli):
    """Test --max-depth limits heading depth in stdin mode."""
    content = "# H1\n## H2-1\n### H3-1\n#### H4-1\n## H2-2\n### H3-2\n"

    result = run_cli(["--max-depth", "2"], stdin=content.encode())

    expected = "- H1\n  - H2-1\n  - H2-2\n"
    assert result.returncode == 0
    assert result.stdout.decode() == expected
    assert result.stderr.decode() == ""


def test_max_depth_1_only_h1s(tmp_path, run_cli, write_md_file):
    """Test --max-depth 1 prints only h1 headings."""
    write_md_file(
        "only_h1.md", "# Title 1\n## Section\n### Subsection\n# Title 2\n## Another Section\n"
    )

    result = run_cli(["--max-depth", "1", str(tmp_path / "only_h1.md")])

    expected = "- Title 1\n- Title 2\n"
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""


def test_max_depth_larger_than_deepest(tmp_path, run_cli, write_md_file):
    """Test --max-depth larger than deepest heading prints everything."""
    write_md_file("shallow.md", "# H1\n## H2\n")

    result = run_cli(["--max-depth", "6", str(tmp_path / "shallow.md")])

    expected = "- H1\n  - H2\n"
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""


def test_max_depth_preserves_indentation(tmp_path, run_cli, write_md_file):
    """Test that filtered headings keep their original indentation."""
    write_md_file(
        "indent.md",
        "# H1\n"
        "## H2\n"
        "### H3-1 (keeps 4-space indent)\n"
        "#### H4 (filtered)\n"
        "### H3-2 (keeps 4-space indent)\n",
    )

    result = run_cli(["--max-depth", "3", str(tmp_path / "indent.md")])

    # H3 headings keep their 4-space indent (2 * (3-1) = 4 spaces)
    expected = (
        "- H1\n  - H2\n    - H3-1 (keeps 4-space indent)\n    - H3-2 (keeps 4-space indent)\n"
    )
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""


def test_max_depth_0_empty_outline(tmp_path, run_cli, write_md_file):
    """Test --max-depth 0 produces empty outline with exit code 0."""
    write_md_file("headings.md", "# H1\n## H2\n### H3\n")

    result = run_cli(["--max-depth", "0", str(tmp_path / "headings.md")])

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_max_depth_negative_error(run_cli):
    """Test --max-depth with negative value produces argparse error (exit code 2)."""
    result = run_cli(["--max-depth", "-1"])

    assert result.returncode == 2
    stderr = result.stderr
    assert "must be >= 0" in stderr
    assert "-1" in stderr
    assert "Traceback" not in stderr


def test_max_depth_invalid_int_error(run_cli):
    """Test --max-depth with non-integer value produces argparse error (exit code 2)."""
    result = run_cli(["--max-depth", "abc"])

    assert result.returncode == 2
    stderr = result.stderr
    assert "invalid int value" in stderr.lower()
    assert "abc" in stderr
    assert "Traceback" not in stderr


def test_max_depth_default_no_filtering(tmp_path, run_cli, write_md_file):
    """Test that without --max-depth, output matches previous behavior (no filtering)."""
    write_md_file("default.md", "# Title\n## Section 1\n### Subsection 1.1\n## Section 2\n")

    result = run_cli([str(tmp_path / "default.md")])

    expected = "- Title\n  - Section 1\n    - Subsection 1.1\n  - Section 2\n"
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""


def test_max_depth_equals_arg(tmp_path, run_cli, write_md_file):
    """Test --max-depth=N syntax works correctly."""
    write_md_file("equals.md", "# H1\n## H2\n### H3\n#### H4\n")

    result = run_cli(["--max-depth=2", str(tmp_path / "equals.md")])

    expected = "- H1\n  - H2\n"
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""
