"""CLI tests for mdoutline."""

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT

    result = subprocess.run(
        [sys.executable, "-m", "mdoutline", str(test_file)],
        cwd=tmp_path.parent.parent,
        env=env,
        capture_output=True,
    )

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

    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT

    result = subprocess.run(
        [sys.executable, "-m", "mdoutline"],
        cwd=tmp_path.parent.parent,
        env=env,
        input=content.encode(),
        capture_output=True,
    )

    expected = "- Title\n  - Section 1\n    - Subsection 1.1\n  - Section 2\n"
    assert result.returncode == 0
    assert result.stdout.decode() == expected
    assert result.stderr.decode() == ""


def test_missing_file(tmp_path):
    """Test error handling for a missing file."""
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT

    result = subprocess.run(
        [sys.executable, "-m", "mdoutline", "NOTES.md"],
        cwd=tmp_path.parent.parent,
        env=env,
        capture_output=True,
    )

    assert result.returncode == 1
    stderr = result.stderr.decode()
    assert "NOTES.md" in stderr
    assert "Traceback" not in stderr
    assert stderr != ""


def test_empty_stdin(tmp_path):
    """Test empty input from stdin."""
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT

    result = subprocess.run(
        [sys.executable, "-m", "mdoutline"],
        cwd=tmp_path.parent.parent,
        env=env,
        input=b"",
        capture_output=True,
    )

    assert result.returncode == 0
    assert result.stdout.decode() == ""
    assert result.stderr.decode() == ""


def test_file_with_no_headings(tmp_path):
    """Test a file with no headings."""
    test_file = tmp_path / "no_headings.md"
    test_file.write_text("Just some text\nMore text\nEven more text\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT

    result = subprocess.run(
        [sys.executable, "-m", "mdoutline", str(test_file)],
        cwd=tmp_path.parent.parent,
        env=env,
        capture_output=True,
    )

    assert result.returncode == 0
    assert result.stdout.decode() == ""
    assert result.stderr.decode() == ""
