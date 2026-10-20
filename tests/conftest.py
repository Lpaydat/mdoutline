"""Shared CLI invocation seam for test suite.

Provides centralized mdoutline binary resolution and subprocess runner.

Two-tier command resolution design:
- Strict resolver (resolve_mdoutline_cmd): script-only resolution for
  deployment-under-test detection. Returns None when no console script
  is available, which test suites use as a skip signal for script-deployment
  tests.
- Runner seam (_require_cmd_and_env): MDOUTLINE_BIN is honored verbatim;
  otherwise the seam probes THIS checkout's source via
  [sys.executable, "-m", "mdoutline"]. A discovered console script is
  deliberately not the default: its editable install imports the main
  checkout's mdoutline.py, never this checkout's (review r1 class 1).
  Any `-m mdoutline` command injects PYTHONPATH=REPO_ROOT so the child
  imports the repo-root module; a script command (MDOUTLINE_BIN only)
  gets no injection, so repo source cannot shadow the installed artifact.

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
    """Resolve mdoutline command and build the child environment.

    Resolution:
    1. MDOUTLINE_BIN, when set and parseable: honored verbatim as the
       deployment-under-test command; runs with the caller's environment
       untouched (injecting PYTHONPATH would let repo source shadow the
       installed artifact under test).
    2. Everything else (no override, or an unparseable/whitespace one):
       [sys.executable, "-m", "mdoutline"], probing THIS checkout's source
       (review r1 class 1). The discovered console script is deliberately
       not the default: its editable install imports the main checkout's
       mdoutline.py, never this checkout's.

    Any `-m mdoutline` command (default or MDOUTLINE_BIN module override)
    injects PYTHONPATH = REPO_ROOT + existing so the child can import the
    repo-root module; script commands get no injection.

    Returns:
        Tuple of (cmd_list, env_dict).
    """
    override = os.environ.get("MDOUTLINE_BIN", "")
    script_cmd = resolve_mdoutline_cmd()
    if override and script_cmd is not None:
        # Operator override, honored verbatim (deployment-under-test runs).
        cmd = script_cmd
    else:
        # Default: probe THIS checkout's source (review r1 class 1). The
        # discovered console script's editable install imports the main
        # checkout's mdoutline.py, so honoring it by default left every
        # CLI pin unable to fail against this checkout's code.
        if override:
            # Override set but unparseable or whitespace-only
            try:
                if not shlex.split(override):
                    print(
                        "mdoutline: warning: MDOUTLINE_BIN set but is empty/whitespace; falling back to python -m mdoutline (probes REPO SOURCE, not a deployed install)",
                        file=sys.stderr,
                    )
            except ValueError as e:
                print(
                    f"mdoutline: warning: MDOUTLINE_BIN '{override}' is unparseable ({e}); falling back to python -m mdoutline (probes REPO SOURCE, not a deployed install)",
                    file=sys.stderr,
                )
        elif script_cmd is None:
            # No override and no console script anywhere (foreign interpreter)
            print(
                "mdoutline: warning: mdoutline console script not installed; falling back to python -m mdoutline (probes REPO SOURCE, not a deployed install)",
                file=sys.stderr,
            )
        cmd = [sys.executable, "-m", "mdoutline"]

    # A `-m mdoutline` invocation needs the repo root importable (foreign-
    # interpreter portability); a script path must NOT get PYTHONPATH - repo
    # source would shadow the installed artifact under test (mdoutline-4ta).
    env = os.environ.copy()
    if any(cmd[i : i + 2] == ["-m", "mdoutline"] for i in range(len(cmd) - 1)):
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
