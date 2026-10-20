"""Tests for '-' as stdin argument."""


def test_dash_argument_reads_from_stdin(run_cli):
    """Positional '-' should read from stdin, same as no argument."""
    content = "# Title\n## Section\n### Subsection\n"
    result_no_arg = run_cli([], stdin=content.encode())
    result_dash = run_cli(["-"], stdin=content.encode())

    assert result_no_arg.returncode == 0
    assert result_dash.returncode == 0
    assert result_no_arg.stdout == result_dash.stdout
    assert result_no_arg.stdout.decode() == "- Title\n  - Section\n    - Subsection\n"


def test_dash_argument_empty_stdin(run_cli):
    """'-' with empty stdin should produce empty output, rc 0."""
    result = run_cli(["-"], stdin=b"")

    assert result.returncode == 0
    assert result.stdout == b""


def test_pipe_with_dash_vs_no_arg(run_cli_pipeline):
    """'doc | mdoutline' vs 'doc | mdoutline -' through a real shell run
    (shell=True, doc piped into the shell's stdin) produce identical output."""
    doc = "# A\n## B\n### C\n"

    result_no_arg = run_cli_pipeline("", stdin=doc)
    result_dash = run_cli_pipeline("-", stdin=doc)

    assert result_no_arg.returncode == 0
    assert result_dash.returncode == 0
    assert result_no_arg.stdout == result_dash.stdout
    assert result_no_arg.stdout == "- A\n  - B\n    - C\n"
