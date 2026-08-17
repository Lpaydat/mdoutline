"""Tests for MDOUTLINE_BIN fallback warnings (Item 8, Items 47y+DJV).

These tests run pytest in a subprocess with --capture=no to ensure that
warnings printed during fixture setup (conftest._require_cmd_and_env)
are captured in stderr. The default pytest output capture (fd-level)
swallows such warnings, so --capture=no is required for verification.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_malformed_mdoutline_bin_warning():
    """TA: Malformed MDOUTLINE_BIN produces warning on stderr.

    Uses VENV interpreter (sys.executable) - the fallback DOES engage here
    because MDOUTLINE_BIN has first precedence, is malformed, so resolver
    returns None, triggering the fallback even though the venv script exists.
    """
    env = {k: v for k, v in os.environ.items() if k != "MDOUTLINE_BIN"}
    env["MDOUTLINE_BIN"] = '"unclosed-quote'

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_cli.py::test_stdin_fallback",
            "--capture=no",
            "-p",
            "no:cacheprovider",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=REPO,
    )
    assert result.returncode == 0, f"Tests failed: {result.stderr}"
    assert "unclosed-quote" in result.stderr, (
        f"Expected 'unclosed-quote' in stderr, got: {result.stderr}"
    )
    assert "MDOUTLINE_BIN" in result.stderr, (
        f"Expected 'MDOUTLINE_BIN' in stderr, got: {result.stderr}"
    )
    assert "REPO SOURCE" in result.stderr, f"Expected 'REPO SOURCE' in stderr, got: {result.stderr}"


def test_foreign_interpreter_not_installed_warning():
    """TB: Foreign interpreter without script installed produces 'not installed' warning."""
    foreign_python = "/usr/bin/python3.14"
    if not Path(foreign_python).exists():
        pytest.skip(f"Foreign interpreter {foreign_python} not found")

    # Precondition check: if mdoutline is on PATH under this interpreter, skip
    env_check = os.environ.copy()
    env_check["PATH"] = "/usr/bin:/bin"
    if shutil.which("mdoutline", path=env_check.get("PATH")):
        pytest.skip(
            f"mdoutline already on PATH for {foreign_python}, cannot test not-installed case"
        )

    env = {k: v for k, v in os.environ.items() if k != "MDOUTLINE_BIN"}
    # Strip venv from PATH and unset MDOUTLINE_BIN
    env["PATH"] = "/usr/bin:/bin"

    result = subprocess.run(
        [foreign_python, "-m", "pytest", "tests/test_cli.py", "-q", "--capture=no"],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=REPO,
    )
    assert result.returncode == 0, f"Tests failed: {result.stderr}"
    assert "not installed" in result.stderr, (
        f"Expected 'not installed' in stderr, got: {result.stderr}"
    )


def test_whitespace_mdoutline_bin_warning():
    """TC: Whitespace-only MDOUTLINE_BIN produces warning on stderr.

    Uses foreign interpreter to ensure fallback engages (whitespace-only
    resolves like unset under strict resolver).
    """
    foreign_python = "/usr/bin/python3.14"
    if not Path(foreign_python).exists():
        pytest.skip(f"Foreign interpreter {foreign_python} not found")

    env = {k: v for k, v in os.environ.items() if k != "MDOUTLINE_BIN"}
    env["PATH"] = "/usr/bin:/bin"
    env["MDOUTLINE_BIN"] = "   "

    result = subprocess.run(
        [foreign_python, "-m", "pytest", "tests/test_cli.py", "-q", "--capture=no"],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=REPO,
    )
    assert result.returncode == 0, f"Tests failed: {result.stderr}"
    assert "MDOUTLINE_BIN" in result.stderr, (
        f"Expected 'MDOUTLINE_BIN' in stderr, got: {result.stderr}"
    )
    assert "REPO SOURCE" in result.stderr, f"Expected 'REPO SOURCE' in stderr, got: {result.stderr}"
