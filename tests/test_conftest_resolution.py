"""Tests for MDOUTLINE_BIN resolution (Item 9)."""

import os

from conftest import resolve_mdoutline_cmd


def test_whitespace_bin_resolves_like_unset(monkeypatch):
    """Whitespace-only MDOUTLINE_BIN values resolve exactly like unset.

    The bead's claim is fall-through EQUIVALENCE: shlex-empty values must not
    short-circuit into an empty command or a crash — they must produce the
    same resolution an unset variable would, whatever the environment yields.
    Asserted pairwise (value vs unset) so the test is meaningful both with a
    script present (baseline = script path) and without one (baseline = None).
    """
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    def resolve(value):
        if value is None:
            monkeypatch.delenv("MDOUTLINE_BIN", raising=False)
        else:
            monkeypatch.setenv("MDOUTLINE_BIN", value)
        return resolve_mdoutline_cmd()

    baseline = resolve(None)
    for value in ["", " ", "\t ", "\t"]:
        result = resolve(value)
        assert result == baseline, (
            f"MDOUTLINE_BIN={value!r} must resolve like unset ({baseline!r}), got {result!r}"
        )


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
