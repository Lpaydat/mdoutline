"""Test that ruff.toml exclude contains required entries (Item 7)."""

import tomllib


def test_ruff_toml_exclude_contains_required_entries():
    """Verify ruff.toml exclude contains .traces, .driver, .pi, .beads."""
    with open("ruff.toml", "rb") as f:
        config = tomllib.load(f)

    exclude = config.get("exclude", [])

    assert ".traces" in exclude, "ruff.toml exclude missing .traces"
    assert ".driver" in exclude, "ruff.toml exclude missing .driver"
    assert ".pi" in exclude, "ruff.toml exclude missing .pi"
    assert ".beads" in exclude, "ruff.toml exclude missing .beads"