"""Test that ruff.toml exclude contains required entries (Item 7)."""

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_ruff_toml_exclude_contains_required_entries():
    """Verify ruff.toml exclude contains .traces, .driver, .pi, .beads."""
    with open("ruff.toml", "rb") as f:
        config = tomllib.load(f)

    exclude = config.get("exclude", [])

    assert ".traces" in exclude, "ruff.toml exclude missing .traces"
    assert ".driver" in exclude, "ruff.toml exclude missing .driver"
    assert ".pi" in exclude, "ruff.toml exclude missing .pi"
    assert ".beads" in exclude, "ruff.toml exclude missing .beads"


def test_excluded_scratch_dir_keeps_sweep_green():
    """Behavior behind the config: a lint-broken file planted in the excluded
    scratch dir (.traces) stays hidden when that dir is swept with gitignore
    respect off - every excluded scratch dir is also gitignored, so this makes
    the exclude list, not .gitignore, the only thing filtering it. The sweep
    is scoped to the planted dir because the config exclude list replaces
    ruff's defaults, leaving a repo-wide pass exposed to a gitignored .venv
    in the main checkout; --force-exclude makes exclusions apply to the
    explicitly-given path (without it ruff bypasses the exclude list there).
    Plant removed in finally."""
    plant = REPO / ".traces" / "ruff_exclude_probe_nbz.py"
    plant.parent.mkdir(parents=True, exist_ok=True)
    # F401 fires `ruff check`; `x=1` fails `ruff format --check`
    plant.write_text("import os\nx=1\n", encoding="utf-8")
    try:
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("RUFF_"):
                del env[key]
        ruff = shutil.which("ruff") or str(REPO / ".venv" / "bin" / "ruff")
        lint = subprocess.run(
            [ruff, "check", "--no-cache", "--no-respect-gitignore", "--force-exclude", ".traces"],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        fmt = subprocess.run(
            [
                ruff,
                "format",
                "--no-cache",
                "--no-respect-gitignore",
                "--force-exclude",
                "--check",
                ".traces",
            ],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert lint.returncode == 0, (
            f"excluded plant tripped ruff check:\n{lint.stdout}{lint.stderr}"
        )
        assert fmt.returncode == 0, f"excluded plant tripped ruff format:\n{fmt.stdout}{fmt.stderr}"
    finally:
        plant.unlink()
