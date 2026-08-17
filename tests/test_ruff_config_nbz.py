"""Test that [tool.ruff] exclude contains required entries."""

import tomllib


def test_ruff_exclude_contains_required_entries():
    """Verify pyproject.toml [tool.ruff] exclude contains .traces, .driver, .pi, .beads."""
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)

    ruff_config = config.get("tool", {}).get("ruff", {})
    exclude = ruff_config.get("exclude", [])

    assert ".traces" in exclude, "[tool.ruff] exclude missing .traces"
    assert ".driver" in exclude, "[tool.ruff] exclude missing .driver"
    assert ".pi" in exclude, "[tool.ruff] exclude missing .pi"
    assert ".beads" in exclude, "[tool.ruff] exclude missing .beads"
