"""Tests for MDOUTLINE_BIN resolution (Item 9)."""

import os

import pytest

from conftest import resolve_mdoutline_cmd


def test_whitespace_bin_resolves_like_unset(monkeypatch):
    """Whitespace-only MDOUTLINE_BIN values resolve to None like unset.

    This test skips if the venv script is available via sysconfig,
    since the sysconfig branch always finds .venv/bin/mdoutline.
    """
    # If we can find the script via sysconfig, skip (sysconfig branch wins)
    import sysconfig
    from pathlib import Path

    scripts_dir = sysconfig.get_path("scripts")
    if Path(scripts_dir).joinpath("mdoutline").exists():
        pytest.skip(
            f"Script exists at {Path(scripts_dir) / 'mdoutline'}, cannot test whitespace-only case"
        )

    # Temporarily remove venv bin from PATH so resolver won't find script
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    for value in [None, "", " ", "\t ", "\t"]:
        if value is None:
            monkeypatch.delenv("MDOUTLINE_BIN", raising=False)
        else:
            monkeypatch.setenv("MDOUTLINE_BIN", value)
        result = resolve_mdoutline_cmd()
        assert result is None, f"MDOUTLINE_BIN={value!r} should resolve to None, got {result}"

    # Restore PATH
    monkeypatch.setenv("PATH", original_path)


def test_valid_path_resolves(monkeypatch, tmp_path):
    """Valid MDOUTLINE_BIN path value resolves correctly."""
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    bin_path = tmp_path / "mdoutline-bin" / "mdoutline"
    bin_path.parent.mkdir(parents=True)
    bin_path.write_text("#!/bin/sh\n")
    bin_path.chmod(0o755)

    monkeypatch.setenv("MDOUTLINE_BIN", str(bin_path))
    result = resolve_mdoutline_cmd()
    assert result is not None, "Valid MDOUTLINE_BIN should resolve"
    assert result[0] == str(bin_path)

    monkeypatch.setenv("PATH", original_path)


def test_multi_token_shlex_value_resolves(monkeypatch):
    """Multi-token MDOUTLINE_BIN value is parsed by shlex."""
    original_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    monkeypatch.setenv("MDOUTLINE_BIN", ".venv/bin/mdoutline --help")
    result = resolve_mdoutline_cmd()
    assert result is not None
    assert result[0] == ".venv/bin/mdoutline"

    monkeypatch.setenv("PATH", original_path)


def test_venv_on_path_with_whitespace_finds_script(monkeypatch, tmp_path):
    """With venv bin on PATH, MDOUTLINE_BIN whitespace resolves to the script."""
    original_path = os.environ.get("PATH", "")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "mdoutline").write_text("#!/bin/sh\n")
    (bin_dir / "mdoutline").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")

    monkeypatch.setenv("MDOUTLINE_BIN", "   ")
    result = resolve_mdoutline_cmd()
    assert result is not None, (
        "With venv on PATH, should resolve script even with whitespace MDOUTLINE_BIN"
    )

    monkeypatch.setenv("PATH", original_path)
