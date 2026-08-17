"""Shared CLI invocation seam for test suite.

Provides centralized mdoutline binary resolution and subprocess runner.

Two-tier command resolution design:
- Strict resolver (resolve_mdoutline_cmd): script-only resolution for
  deployment-under-test detection. Returns None when no console script
  is available, which test suites use as a skip signal for script-deployment
  tests.
- Runner-level fallback (_require_cmd_and_env): when the strict resolver
  returns None, falls back to [sys.executable, "-m", "mdoutline"] for
  foreign-interpreter portability. This allows tests to run under any
  Python interpreter when the repo root is on PYTHONPATH.

The scripts dir comes from sysconfig under the ACTIVE interpreter - never
derived from the interpreter executable's own path, which would follow
symlinks out of the venv to the base interpreter's install dir.
"""

import os
import shlex
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

TIMEOUT_S = 120


def resolve_mdoutline_cmd() -> list[str] | None:
    """Resolve mdoutline CLI command as argv list, or None if not found.

    Strict script-only resolver for deployment-under-test detection.
    Returns None when no console script is available - test suites use
    this as a skip signal for script-deployment tests. The -m fallback
    is handled at the runner level (_require_cmd_and_env), not here.

    Precedence:
    1. MDOUTLINE_BIN env var (operator override, trusted blindly)
       An unparseable override is treated as not-found (resolver-empty), not an error.
    2. shutil.which("mdoutline")
    3. sysconfig.get_path("scripts") / "mdoutline"
    4. None (caller may fall back to [sys.executable, "-m", "mdoutline"])
    """
    try:
        if cmd := shlex.split(os.environ.get("MDOUTLINE_BIN", "")):
            return cmd
    except ValueError:
        # Malformed MDOUTLINE_BIN (e.g., unclosed quote) - treat as not-found
        return None

    if found := shutil.which("mdoutline"):
        return [found]

    candidate = Path(sysconfig.get_path("scripts")) / "mdoutline"
    if candidate.exists():
        return [str(candidate)]

    return None


REPO_ROOT = Path(__file__).resolve().parent.parent


def _require_cmd_and_env() -> tuple[list[str], dict[str, str]]:
    """Resolve mdoutline command and build environment with PYTHONPATH.

    Two-tier resolution for portability:
    1. Strict script resolver (MDOUTLINE_BIN -> console script on PATH ->
       sysconfig scripts dir). Used for deployment-under-test detection.
    2. Fallback to [sys.executable, "-m", "mdoutline"] when no script is
       found, enabling tests under any interpreter when repo root is on
       PYTHONPATH (foreign-interpreter portability).

    Returns:
        Tuple of (cmd_list, env_dict).
    """
    cmd = resolve_mdoutline_cmd()
    if cmd is None:
        # Emit warning when resolver returns None
        mdoutline_bin = os.environ.get("MDOUTLINE_BIN", "")
        if mdoutline_bin:
            # Try to parse to see if it's malformed or whitespace-only
            try:
                parsed = shlex.split(mdoutline_bin)
                if not parsed:
                    # Whitespace-only
                    print(
                        "mdoutline: warning: MDOUTLINE_BIN set but is empty/whitespace; falling back to python -m mdoutline (probes REPO SOURCE, not a deployed install)",
                        file=sys.stderr,
                    )
                # If parsed, the setter override was explicitly invalid/unparseable
            except ValueError as e:
                # Malformed (e.g., unclosed quote)
                print(
                    f"mdoutline: warning: MDOUTLINE_BIN '{mdoutline_bin}' is unparseable ({e}); falling back to python -m mdoutline (probes REPO SOURCE, not a deployed install)",
                    file=sys.stderr,
                )
        else:
            # Not set
            print(
                "mdoutline: warning: mdoutline console script not installed; falling back to python -m mdoutline (probes REPO SOURCE, not a deployed install)",
                file=sys.stderr,
            )
        cmd = [sys.executable, "-m", "mdoutline"]

    env = os.environ.copy()
    pythonpath = str(REPO_ROOT)
    if existing := os.environ.get("PYTHONPATH"):
        pythonpath += os.pathsep + existing
    env["PYTHONPATH"] = pythonpath

    return cmd, env


@pytest.fixture
def run_cli():
    """Fixture returning a callable to run mdoutline CLI subprocess."""

    def runner(args, *, stdin=None, cwd=None, timeout=TIMEOUT_S) -> subprocess.CompletedProcess:
        cmd, env = _require_cmd_and_env()

        # Binary mode when stdin is bytes, text mode otherwise
        text_mode = not isinstance(stdin, bytes)

        return subprocess.run(
            cmd + list(args),
            input=stdin,
            text=text_mode,
            capture_output=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )

    return runner


@pytest.fixture
def run_cli_pipeline():
    """Fixture returning a callable to run mdoutline in a shell pipeline."""

    def runner(
        command_suffix: str,
        *,
        stdin: str,
        cwd=None,
        timeout=TIMEOUT_S,
        executable: str | None = None,
    ) -> subprocess.CompletedProcess:
        cmd, env = _require_cmd_and_env()

        full_command = shlex.join(cmd) + " " + command_suffix

        return subprocess.run(
            full_command,
            shell=True,
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            executable=executable,
        )

    return runner


@pytest.fixture
def write_md_file(tmp_path):
    """Fixture returning a callable to write markdown files to tmp_path."""

    def writer(name: str, content: str) -> Path:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path

    return writer
