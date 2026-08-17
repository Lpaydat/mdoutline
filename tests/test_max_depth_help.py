"""Tests for --max-depth help string (Item lg8)."""


def test_max_depth_help_output(run_cli):
    """--max-depth help should not claim '1-6' range."""
    result = run_cli(["--help"])

    assert result.returncode == 0
    help_text = result.stdout
    # Should contain the new wording
    assert "maximum heading depth to include" in help_text
    # Should NOT contain '1-6'
    assert "1-6" not in help_text


def test_max_depth_7_same_as_no_flag(run_cli, write_md_file):
    """--max-depth 7 should produce the same output as no flag."""
    test_file = write_md_file(
        "doc.md",
        "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6\n",
    )

    result_no_flag = run_cli([str(test_file)])
    result_max7 = run_cli(["--max-depth", "7", str(test_file)])

    assert result_no_flag.returncode == 0
    assert result_max7.returncode == 0
    # Handle both str and bytes output
    out1 = (
        result_no_flag.stdout.decode()
        if isinstance(result_no_flag.stdout, bytes)
        else result_no_flag.stdout
    )
    out2 = (
        result_max7.stdout.decode() if isinstance(result_max7.stdout, bytes) else result_max7.stdout
    )
    assert out1 == out2
