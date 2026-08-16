"""CLI tests for mdoutline."""

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_mdoutline(args=None, input_data=None, cwd=None):
    """Helper to run mdoutline with proper environment."""
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT
    cmd = [sys.executable, "-m", "mdoutline"]
    if args:
        cmd.extend(args)
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        env=env,
        input=input_data,
        capture_output=True,
    )


def test_file_argument(tmp_path):
    """Test reading from a file argument."""
    test_file = tmp_path / "test.md"
    test_file.write_text(
        "# Title\n"
        "## Section 1\n"
        "### Subsection 1.1\n"
        "## Section 2\n"
        "### Subsection 2.1\n"
        "#### Sub-subsection 2.1.1\n"
    )

    result = _run_mdoutline([str(test_file)])

    expected = (
        "- Title\n"
        "  - Section 1\n"
        "    - Subsection 1.1\n"
        "  - Section 2\n"
        "    - Subsection 2.1\n"
        "      - Sub-subsection 2.1.1\n"
    )
    assert result.returncode == 0
    assert result.stdout.decode() == expected
    assert result.stderr.decode() == ""


def test_stdin_fallback(tmp_path):
    """Test reading from stdin when no file argument is provided."""
    content = "# Title\n## Section 1\n### Subsection 1.1\n## Section 2\n"

    result = _run_mdoutline(input_data=content.encode())

    expected = "- Title\n  - Section 1\n    - Subsection 1.1\n  - Section 2\n"
    assert result.returncode == 0
    assert result.stdout.decode() == expected
    assert result.stderr.decode() == ""


def test_missing_file(tmp_path):
    """Test error handling for a missing file."""
    result = _run_mdoutline(["NOTES.md"])

    assert result.returncode == 1
    stderr = result.stderr.decode()
    assert "NOTES.md" in stderr
    assert "Traceback" not in stderr
    assert stderr != ""


def test_empty_stdin(tmp_path):
    """Test empty input from stdin."""
    result = _run_mdoutline(input_data=b"")

    assert result.returncode == 0
    assert result.stdout.decode() == ""
    assert result.stderr.decode() == ""


def test_file_with_no_headings(tmp_path):
    """Test a file with no headings."""
    test_file = tmp_path / "no_headings.md"
    test_file.write_text("Just some text\nMore text\nEven more text\n")

    result = _run_mdoutline([str(test_file)])

    assert result.returncode == 0
    assert result.stdout.decode() == ""
    assert result.stderr.decode() == ""


def test_broken_pipe_no_traceback(tmp_path):
    """Test broken pipe produces no traceback, and consumer receives content."""
    # Generate a large outline that exceeds pipe buffer (~64KB)
    lines = [f"# Heading {i}\n## Sub {i}\n### Subsub {i}\n" for i in range(5000)]
    content = "".join(lines)

    # Use shell pipe to head -1 which closes the pipe early
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT

    # Using shell=True to enable the pipe
    result = subprocess.run(
        f"{sys.executable} -m mdoutline | head -1",
        shell=True,
        cwd=REPO_ROOT,
        env=env,
        input=content.encode(),
        capture_output=True,
    )

    stdout = result.stdout.decode()
    stderr = result.stderr.decode()

    # Should get the first line of output
    assert stdout == "- Heading 0\n"
    # No traceback and no BrokenPipeError message in stderr
    assert "Traceback" not in stderr
    assert "BrokenPipeError" not in stderr
    # The actual exit code from head (0), not the SIGPIPE from mdoutline
    assert result.returncode == 0


def test_bom_file(tmp_path):
    """Test UTF-8 BOM is handled correctly for file input."""
    test_file = tmp_path / "bom.md"
    # Write BOM + content
    bom_content = b"\xef\xbb\xbf# Title\n## Section\n"
    test_file.write_bytes(bom_content)

    result = _run_mdoutline([str(test_file)])

    expected = "- Title\n  - Section\n"
    assert result.returncode == 0
    assert result.stdout.decode() == expected
    assert result.stderr.decode() == ""


def test_bom_stdin():
    """Test UTF-8 BOM is handled correctly for stdin input."""
    bom_content = b"\xef\xbb\xbf# Title\n## Section\n"

    result = _run_mdoutline(input_data=bom_content)

    expected = "- Title\n  - Section\n"
    assert result.returncode == 0
    assert result.stdout.decode() == expected
    assert result.stderr.decode() == ""


def test_empty_string_argument():
    """Test empty string argument is treated as missing file, not stdin."""
    result = _run_mdoutline([""])

    assert result.returncode == 1
    stderr = result.stderr.decode()
    # Should contain the error about reading empty filename
    assert "cannot read" in stderr.lower()
    assert "Traceback" not in stderr
    assert stderr != ""


def test_invalid_utf8_stdin():
    """Test invalid UTF-8 on stdin produces proper error message."""
    # Invalid UTF-8 bytes
    invalid_utf8 = b"\xff\xfe\x00\x00"

    result = _run_mdoutline(input_data=invalid_utf8)

    assert result.returncode == 1
    stderr = result.stderr.decode()
    # Should name stdin, not 'None'
    assert "stdin" in stderr.lower()
    assert "None" not in stderr
    assert "Traceback" not in stderr
    assert stderr != ""
