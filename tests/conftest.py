"""Shared CLI invocation seam for test suite.

Provides centralized mdoutline binary resolution and subprocess runner.
The scripts dir comes from sysconfig under the ACTIVE interpreter - never
derived from the interpreter executable's own path, which would follow
symlinks out of the venv to the base interpreter's install dir.
"""

import os
import shlex
import shutil
import subprocess
import sysconfig
from pathlib import Path

import pytest

TIMEOUT_S = 120


def resolve_mdoutline_cmd() -> list[str] | None:
    """Resolve mdoutline CLI command as argv list, or None if not found.

    Precedence:
    1. MDOUTLINE_BIN env var (operator override, trusted blindly)
    2. shutil.which("mdoutline")
    3. sysconfig.get_path("scripts") / "mdoutline"
    4. None
    """
    if mdoutline_bin := os.environ.get("MDOUTLINE_BIN"):
        return shlex.split(mdoutline_bin)

    if found := shutil.which("mdoutline"):
        return [found]

    candidate = Path(sysconfig.get_path("scripts")) / "mdoutline"
    if candidate.exists():
        return [str(candidate)]

    return None


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def run_cli():
    """Fixture returning a callable to run mdoutline CLI subprocess."""

    def runner(args, *, stdin=None, cwd=None, timeout=TIMEOUT_S) -> subprocess.CompletedProcess:
        cmd = resolve_mdoutline_cmd()
        if cmd is None:
            raise RuntimeError("mdoutline command not found - skip test with appropriate reason")

        env = os.environ.copy()
        pythonpath = str(REPO_ROOT)
        if existing := os.environ.get("PYTHONPATH"):
            pythonpath += os.pathsep + existing
        env["PYTHONPATH"] = pythonpath

        return subprocess.run(
            cmd + list(args),
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
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
