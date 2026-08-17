"""Independent behavior verification: [ticket-refactor-02] C3 — dead [tool.ruff] block deleted.

Second-wave suite (written blind from the spec card, not derived from
tests/test_behavior_ruff_config.py). Spec requirements proven here by EXECUTION:

  R1. pyproject.toml at HEAD carries no [tool.ruff]/[tool.ruff.lint] tables.
  R2. The change is a pure deletion: parent blob minus the removed lines is
      byte-identical to the HEAD blob (nothing else was touched).
  R3. The deleted block was dead AND a strict subset of ruff.toml at the
      moment of deletion (spec's "strict superset" claim, checked from git
      history, not from the spec's prose).
  R4. ruff.toml is the config actually in effect — from the repo root AND
      from a nested subdirectory (ancestor discovery), with RUFF_* env
      scrubbed (deployment realism).
  R5. Effective lint behavior (select families firing, E501 ignored) comes
      from ruff.toml; a mangled pyproject block changes nothing.
  R6. No tracked non-test file references the deleted block (no consumer
      left behind: build, docs, CI, Makefile).
  R7. Deployment readiness: wheel builds from the edited pyproject.toml and
      the installed console script still works (via the project's shared
      conftest seam).
"""

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TIMEOUT_S = 120

RUFF_TOML_BODY = (
    "line-length = 100\n"
    'target-version = "py311"\n'
    "\n"
    "[lint]\n"
    'select = ["E", "F", "W", "I", "UP", "B", "SIM"]\n'
    'ignore = ["E501"]\n'
    "\n"
    "[lint.isort]\n"
    'known-first-party = ["mdoutline"]\n'
)

# Probe with violations from the selected families plus one over-long line
# (E501) that must stay ignored. Import order is deliberately unsorted (I001),
# x is unused (F841), mutable default (B006).
VIOLATIONS_PROBE = """import sys
import mdoutline


def probe() -> None:
    x = 41  # F841
    return None


def acc(items: list = []) -> list:  # B006
    return items


acc(), print(sys, mdoutline)
# E501 must stay ignored: this comment is deliberately far longer than one hundred characters so E501 would fire if the ignore list were lost.
"""


# ---------------------------------------------------------------- helpers


def find_ruff() -> str:
    """PATH first (what Makefile uses), then the repo venv."""
    found = shutil.which("ruff")
    if found:
        return found
    venv_ruff = REPO / ".venv" / "bin" / "ruff"
    if venv_ruff.exists():
        return str(venv_ruff)
    pytest.fail("ruff binary not found on PATH or in .venv")


def clean_env(extra: dict | None = None) -> dict:
    """Copy of os.environ with RUFF_* scrubbed so probes measure only files."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("RUFF_")}
    if extra:
        env.update(extra)
    return env


def run(cmd: list[str], *, cwd: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_S, env=clean_env(extra_env)
    )


def show_settings(ruff: str, cwd: Path, target: str) -> str:
    proc = run([ruff, "check", "--no-cache", "--show-settings", target], cwd=cwd)
    assert proc.returncode == 0, f"show-settings failed in {cwd}:\n{proc.stderr}"
    return proc.stdout


def settings_path(dump: str) -> str:
    line = next((ln for ln in dump.splitlines() if ln.startswith("Settings path:")), "")
    if '"' not in line:
        return ""
    return line.split('"')[1]


def effective_line_length(dump: str) -> int:
    m = re.search(r"^linter\.line_length = (\d+)$", dump, re.M)
    assert m, "line_length not found in settings dump"
    return int(m.group(1))


def c3_commit() -> str:
    """The commit that changed the count of '[tool.ruff]' in pyproject.toml."""
    proc = run(
        ["git", "log", "-1", "--format=%H", "-S[tool.ruff]", "--", "pyproject.toml"], cwd=REPO
    )
    assert proc.returncode == 0, proc.stderr
    sha = proc.stdout.strip()
    assert sha, "no commit in pyproject.toml history touched [tool.ruff]"
    return sha


def git_blob(sha: str, path: str) -> str:
    proc = run(["git", "show", f"{sha}:{path}"], cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def deleted_line_numbers(sha: str, path: str) -> dict[int, str]:
    """Line numbers (1-based, in the PARENT blob) removed by commit `sha`,
    anchored by the diff hunk header — not by content matching, which is
    ambiguous for blank/duplicate lines.

    Returns {parent_line_no: removed_content}.
    """
    proc = run(["git", "diff", "-U0", f"{sha}^", sha, "--", path], cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    removed: dict[int, str] = {}
    hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")
    current: int | None = None
    for ln in proc.stdout.splitlines():
        m = hunk_re.match(ln)
        if m:
            current = int(m.group(1))
            continue
        if current is None:
            continue
        if ln.startswith("-"):
            removed[current] = ln[1:]
            current += 1
    return removed


def test_r2_change_is_pure_deletion_byte_identical():
    """Parent blob minus the removed LINES (anchored by hunk position) is
    byte-identical to the HEAD blob — nothing but the block was deleted."""
    sha = c3_commit()
    parent = git_blob(f"{sha}^", "pyproject.toml")
    head = git_blob(sha, "pyproject.toml")

    numstat = run(["git", "diff-tree", "--no-commit-id", "--numstat", "-r", sha], cwd=REPO)
    files = [ln.split("\t") for ln in numstat.stdout.splitlines()]
    assert len(files) == 1 and files[0][2] == "pyproject.toml", f"not a single-file change: {files}"
    added, deleted = files[0][0], files[0][1]
    assert (added, deleted) == ("0", "8"), f"not 0-ins/8-del: {files}"

    removed = deleted_line_numbers(sha, "pyproject.toml")
    assert len(removed) == 8, f"expected 8 removed lines, anchored {len(removed)}"
    parent_lines = parent.splitlines(keepends=True)
    for no, content in removed.items():
        actual = parent_lines[no - 1].rstrip("\r\n")
        assert actual == content, f"line {no}: diff says removed {content!r}, parent has {actual!r}"
    reconstructed = "".join(
        line for idx, line in enumerate(parent_lines, start=1) if idx not in removed
    )
    assert reconstructed == head, "parent-minus-deleted-lines != HEAD blob"


# ------------------------------------------- R1/R2: what exactly was deleted


def test_r1_head_pyproject_has_only_minimal_ruff_table():
    """pyproject.toml has at most a minimal [tool.ruff] table (exclude only).

    The old dead block (line-length, target-version, select, ignore) was
    deleted by ticket-refactor-02. mdoutline-nbz added only the exclude list.
    """
    parsed = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    tool = parsed.get("tool", {})
    if "ruff" in tool:
        ruff_keys = set(tool["ruff"].keys())
        assert ruff_keys == {"exclude"}, f"tool.ruff should only have 'exclude', got: {ruff_keys}"
    assert not any(k.startswith("ruff") for k in tool if k != "ruff"), (
        f"ruff-adjacent tool keys: {sorted(k for k in tool if k.startswith('ruff'))}"
    )


# ----------------------------- R3: deleted block was dead AND strict subset


def test_r3_deleted_block_was_strict_subset_of_ruff_toml():
    """Spec claim checked from history: every value in the deleted block is
    present with the same value in ruff.toml at the deletion commit, which
    additionally carries [lint.isort] (strict superset)."""
    sha = c3_commit()
    parent_cfg = tomllib.loads(git_blob(f"{sha}^", "pyproject.toml"))["tool"]["ruff"]
    ruff_cfg = tomllib.loads(git_blob(sha, "ruff.toml"))

    assert parent_cfg["line-length"] == ruff_cfg["line-length"] == 100
    assert parent_cfg["target-version"] == ruff_cfg["target-version"] == "py311"
    assert parent_cfg["lint"]["select"] == ruff_cfg["lint"]["select"]
    assert parent_cfg["lint"]["ignore"] == ruff_cfg["lint"]["ignore"]
    assert ruff_cfg["lint"]["isort"]["known-first-party"] == ["mdoutline"], "superset key missing"
    assert "isort" not in parent_cfg["lint"], "deleted block was NOT a strict subset"

    # and ruff.toml is untouched since: byte-identical to today's file
    assert git_blob(sha, "ruff.toml") == (REPO / "ruff.toml").read_text(encoding="utf-8")


def test_r5_mangled_pyproject_block_is_dead_minimal_tree(tmp_path):
    """Deadness on a hand-built minimal tree (no git machinery): with ruff.toml
    present, a MANGLED pyproject [tool.ruff] block (line-length=7, select=["E"])
    must not move effective settings; without ruff.toml the same block IS
    honored — proving the probe is sensitive and the block dead, not magic."""
    ruff = find_ruff()
    mangled = '[tool.ruff]\nline-length = 7\n\n[tool.ruff.lint]\nselect = ["E"]\n'
    (tmp_path / "pyproject.toml").write_text(mangled, encoding="utf-8")
    (tmp_path / "probe.py").write_text("y = 2\n", encoding="utf-8")

    # control first: no ruff.toml -> mangled block IS live (probe sensitivity)
    dump = show_settings(ruff, tmp_path, "probe.py")
    assert settings_path(dump).endswith("pyproject.toml"), (
        "control: expected pyproject as settings path"
    )
    assert effective_line_length(dump) == 7, "control: mangled block not honored without ruff.toml"

    # now add ruff.toml -> block must go completely dead
    (tmp_path / "ruff.toml").write_text(RUFF_TOML_BODY, encoding="utf-8")
    dump = show_settings(ruff, tmp_path, "probe.py")
    assert settings_path(dump).endswith("ruff.toml"), "ruff.toml present but not the settings path"
    assert effective_line_length(dump) == 100, (
        "mangled pyproject block leaked into effective settings"
    )


# ------------------------- R4: ruff.toml in effect (root AND subdirectory)


def test_r4_settings_path_resolves_to_ruff_toml_from_root():
    ruff = find_ruff()
    dump = show_settings(ruff, REPO, "mdoutline.py")
    assert settings_path(dump) == str(REPO / "ruff.toml"), (
        f"unexpected settings path: {settings_path(dump)!r}"
    )
    assert effective_line_length(dump) == 100
    assert "linter.unresolved_target_version = 3.11" in dump


def test_r4_ancestor_discovery_from_nested_subdir(tmp_path):
    """Running ruff from a deeply nested cwd must still find the repo-root-style
    ruff.toml via ancestor walk — the deletion must not have disturbed the
    layout ruff's discovery depends on."""
    ruff = find_ruff()
    root = tmp_path / "proj"
    deep = root / "src" / "pkg" / "inner"
    deep.mkdir(parents=True)
    (root / "ruff.toml").write_text(RUFF_TOML_BODY, encoding="utf-8")
    (deep / "mod.py").write_text("z = 3\n", encoding="utf-8")
    dump = show_settings(ruff, deep, "mod.py")
    assert settings_path(dump) == str(root / "ruff.toml"), (
        f"ancestor discovery broke: {settings_path(dump)!r}"
    )
    assert effective_line_length(dump) == 100


def test_r4_repo_tests_subdir_still_sees_root_config():
    """In the real repo, invoking ruff with cwd=tests/ (a true subdir) still
    resolves the root ruff.toml for a root-level file."""
    ruff = find_ruff()
    proc = run(
        [ruff, "check", "--no-cache", "--show-settings", "../mdoutline.py"], cwd=REPO / "tests"
    )
    assert proc.returncode == 0, proc.stderr
    assert settings_path(proc.stdout) == str(REPO / "ruff.toml")


# ------------------- R5: rule firing driven by ruff.toml, not pyproject


def test_r5_rule_firing_from_ruff_toml_select_and_ignore(tmp_path):
    ruff = find_ruff()
    (tmp_path / "ruff.toml").write_text(RUFF_TOML_BODY, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.ruff]\nline-length = 7\n\n[tool.ruff.lint]\nselect = ["E"]\n', encoding="utf-8"
    )
    (tmp_path / "probe.py").write_text(VIOLATIONS_PROBE, encoding="utf-8")
    proc = run([ruff, "check", "--no-cache", "--output-format", "json", "probe.py"], cwd=tmp_path)
    assert proc.returncode == 1, f"expected violations, rc={proc.returncode}, out={proc.stdout}"
    codes = {f["code"] for f in json.loads(proc.stdout)}
    assert "F841" in codes and "B006" in codes and "I001" in codes, (
        f'selected families did not all fire — pyproject select=["E"] leaked? codes={sorted(codes)}'
    )
    assert "E501" not in codes, f'E501 fired despite ignore=["E501"]: {sorted(codes)}'


def test_r5_probe_is_sensitive_control_without_ruff_toml(tmp_path):
    """Same probe, mangled pyproject only: F841/B006/I001 must NOT fire —
    proves the firing test above distinguishes the two configurations."""
    ruff = find_ruff()
    (tmp_path / "pyproject.toml").write_text(
        '[tool.ruff]\nline-length = 7\n\n[tool.ruff.lint]\nselect = ["E"]\n', encoding="utf-8"
    )
    (tmp_path / "probe.py").write_text(VIOLATIONS_PROBE, encoding="utf-8")
    proc = run([ruff, "check", "--no-cache", "--output-format", "json", "probe.py"], cwd=tmp_path)
    codes = {f["code"] for f in json.loads(proc.stdout)} if proc.stdout.strip() else set()
    assert not ({"F841", "B006", "I001"} & codes), (
        f'control failed: non-E families fired under select=["E"]: {sorted(codes)}'
    )


def test_r5_repo_lint_and_format_green():
    ruff = find_ruff()
    lint = run([ruff, "check", "--no-cache", "."], cwd=REPO)
    assert lint.returncode == 0, f"ruff check . failed:\n{lint.stdout}\n{lint.stderr}"
    fmt = run([ruff, "format", "--no-cache", "--check", "."], cwd=REPO)
    assert fmt.returncode == 0, f"ruff format --check . failed:\n{fmt.stdout}\n{fmt.stderr}"


# ------------------------------------------ R6: no orphaned consumers


def test_r6_no_tracked_non_test_file_references_the_block():
    proc = run(["git", "grep", "-l", "-F", "tool.ruff", "HEAD"], cwd=REPO)
    matches = [ln.split(":", 1)[1] for ln in proc.stdout.splitlines() if ln.strip()]
    offenders = [m for m in matches if not m.startswith("tests/")]
    assert not offenders, f"tracked non-test files still reference tool.ruff: {offenders}"


# ------------------------------------- R7: deployment readiness


def test_r7_wheel_builds_from_edited_pyproject(tmp_path_factory):
    """pyproject.toml is also the BUILD file: the edited file must still build
    a wheel containing the module and the console-script entry point."""
    pip = str(REPO / ".venv" / "bin" / "pip")
    if not Path(pip).exists():
        pytest.skip("repo .venv pip unavailable")
    out_dir = tmp_path_factory.mktemp("wheel")
    proc = subprocess.run(
        [pip, "wheel", "--no-deps", "-w", str(out_dir), "."],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=600,
        env=clean_env(),
    )
    assert proc.returncode == 0, f"pip wheel failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    whls = sorted(out_dir.glob("mdoutline-*.whl"))
    assert len(whls) == 1, f"expected exactly one wheel, got {[w.name for w in whls]}"
    listing = subprocess.run(
        [str(REPO / ".venv" / "bin" / "python"), "-m", "zipfile", "-l", str(whls[0])],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
    )
    assert "mdoutline.py" in listing.stdout, "module missing from wheel"
    assert "entry_points.txt" in listing.stdout, "console script entry point missing from wheel"


def test_r7_console_script_runs_via_conftest_seam(run_cli):
    """The packaged CLI still works after the pyproject edit (the edit zone is
    two tables above [project.scripts]). Uses the project's shared seam."""
    proc = run_cli([], stdin="# Alpha\n## Beta\n")
    assert proc.returncode == 0, proc.stderr
    assert "Alpha" in proc.stdout and "Beta" in proc.stdout
