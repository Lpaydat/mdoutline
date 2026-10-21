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


def test_dash_invalid_utf8_stdin_names_stdin(run_cli):
    """'-' with invalid UTF-8 on stdin must name '<stdin>' in the error.

    Spec: '-' behaves exactly like no argument, including the '<stdin>'
    source name in error paths (docs/specs/mdoutline.md).
    """
    result = run_cli(["-"], stdin=b"\xff\xfe\x00\x00")

    assert result.returncode == 1
    stderr = result.stderr.decode()
    # Exactly one line starting with "mdoutline: cannot read '<stdin>':"
    lines = stderr.strip().split("\n")
    assert len(lines) == 1
    assert lines[0].startswith("mdoutline: cannot read '<stdin>':")
    # The source name is '<stdin>', never the literal '-' argument
    assert "'-'" not in stderr
    # No traceback
    assert "Traceback" not in stderr


def test_dash_closed_stdin_names_stdin(run_cli_pipeline):
    """'-' with a closed stdin (0<&-) must name <stdin> in the error.

    Same error-path naming claim as above, through the closed-fd path
    (mirrors the closed-stdout pin's style).
    """
    result = run_cli_pipeline("- 0<&-", stdin="", executable="/bin/bash")

    assert result.returncode == 1
    stderr = result.stderr
    # Exactly one line starting with "mdoutline: cannot read <stdin>:"
    lines = stderr.strip().split("\n")
    assert len(lines) == 1
    assert lines[0].startswith("mdoutline: cannot read <stdin>:")
    # No traceback
    assert "Traceback" not in stderr


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
