"""Behavior verification: [ticket-refactor-02] C3 — dead [tool.ruff] block deleted from pyproject.toml.

Spec claims under test (commit 6a23435, pure 8-line deletion):
  S1. pyproject.toml carries NO [tool.ruff] / [tool.ruff.lint] tables after the change.
  S2. ruff.toml is KEPT, intact, and is the config actually in effect (Settings path).
  S3. Zero behavior change: effective ruff settings and rule firing are identical
      pre-deletion vs post-deletion; the deleted block was dead.

Method: every claim is proven by EXECUTION — `ruff check --show-settings`,
`ruff check` on probe files with real violations, and `git archive` trees that
reconstruct the pre-change configuration. No reading-of-code assertions beyond
the config files that ARE the deliverable.
"""

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TIMEOUT_S = 60


# ---------------------------------------------------------------- helpers


def find_ruff() -> str:
    """Locate ruff: PATH first, then the repo venv (canonical per Makefile)."""
    found = shutil.which("ruff")
    if found:
        return found
    venv_ruff = REPO / ".venv" / "bin" / "ruff"
    if venv_ruff.exists():
        return str(venv_ruff)
    raise RuntimeError("ruff binary not found on PATH or in .venv")


def find_git() -> str:
    git = shutil.which("git")
    if not git:
        raise RuntimeError("git binary not found")
    return git


def run(cmd: list[str], *, cwd: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Ruff would honor RUFF_* env vars over files; scrub them so probes measure
    # only the config files under test (deployment realism).
    for key in list(env):
        if key.startswith("RUFF_"):
            del env[key]
    if env_extra:
        env.update(env_extra)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_S, env=env)


def ruff_show_settings(ruff: str, tree: Path) -> str:
    """Effective settings dump for a file guaranteed present in every tree."""
    proc = run([ruff, "check", "--no-cache", "--show-settings", "mdoutline.py"], cwd=tree)
    assert proc.returncode == 0, f"show-settings failed in {tree}:\n{proc.stderr}"
    return proc.stdout


def normalize(text: str, tree: Path) -> str:
    """Scrub tree-specific absolute paths so dumps from different trees diff cleanly."""
    return text.replace(str(tree), "<TREE>")


def c3_commit_sha(git: str) -> str:
    """The commit that deleted the dead [tool.ruff] block (= C3).

    Pinned to the historical C3 sha rather than pickaxed at runtime:
    subsequent commits legitimately re-add/remove [tool.ruff] content in
    pyproject.toml (e.g. mdoutline-nbz), which would silently re-anchor a
    ``-S[tool.ruff]`` pickaxe onto unrelated churn.
    """
    return "6a23435ea082df5c3e201a16aa7766512d1aba23"


def build_tree(git: str, dest: Path, *, pyproject_blob: str | None = None) -> Path:
    """Materialize HEAD as a plain tree (no .git); optionally swap in a pyproject blob."""
    dest.mkdir(parents=True, exist_ok=True)
    # NB: git archive output is a BINARY tar stream — must NOT go through the
    # text-decoding `run` wrapper.
    archive = subprocess.run(
        [git, "archive", "HEAD"],
        cwd=REPO,
        capture_output=True,
        timeout=TIMEOUT_S,
    )
    assert archive.returncode == 0, archive.stderr
    untar = subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, timeout=TIMEOUT_S)
    assert untar.returncode == 0, "tar extraction of git archive failed"
    if pyproject_blob is not None:
        (dest / "pyproject.toml").write_text(pyproject_blob, encoding="utf-8")
    return dest


def parent_pyproject(git: str) -> str:
    """pyproject.toml as it was BEFORE the C3 deletion (still carrying the dead block)."""
    sha = c3_commit_sha(git)
    proc = run([git, "show", f"{sha}^:pyproject.toml"], cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    blob = proc.stdout
    assert "[tool.ruff]" in blob, "pre-C3 pyproject unexpectedly lacks the [tool.ruff] block"
    return blob


VIOLATIONS_PROBE = '''"""Probe file with violations ruff.toml must catch (and one it must ignore)."""

import mdoutline
import sys
import pytest


def unused_import() -> None:
    x = 1  # F841 local variable assigned but never used
    return None


def mutable_default(items: list = []) -> list:  # B006 mutable-argument-default
    return items


def simulate() -> None:
    print(sys.maxsize, pytest.__version__, mdoutline.__doc__)


# E501 must stay IGNORED: this comment line is deliberately far longer than one hundred characters so that pycodestyle's line-too-long rule would fire if the ignore list were lost or changed in any way at all.
'''

FORMAT_PROBE = "x=1\ny = [ 1,2, 3 ]\n"


# ---------------------------------------------------- S1: block is gone


def test_pyproject_has_no_ruff_table():
    """S1: no [tool.ruff] heading of any kind remains in pyproject.toml."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.ruff" not in text, "pyproject.toml still carries a [tool.ruff*] table"
    parsed = tomllib.loads(text)
    assert "ruff" not in parsed.get("tool", {}), "tool.ruff key survives TOML parse"


def test_pyproject_valid_and_neighbour_tables_intact():
    """The deletion clipped nothing around it: file parses, project tables survive."""
    parsed = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert parsed["project"]["name"] == "mdoutline"
    assert parsed["project"]["scripts"] == {"mdoutline": "mdoutline:main"}
    assert parsed["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]
    assert parsed["build-system"]["build-backend"] == "setuptools.build_meta"


# ---------------------------------------------------- S2: ruff.toml in effect


def test_ruff_toml_kept_with_pinned_values():
    """S2: ruff.toml kept with exactly the documented strict-superset values."""
    parsed = tomllib.loads((REPO / "ruff.toml").read_text(encoding="utf-8"))
    assert parsed["line-length"] == 100
    assert parsed["target-version"] == "py311"
    assert parsed["lint"]["select"] == ["E", "F", "W", "I", "UP", "B", "SIM"]
    assert parsed["lint"]["ignore"] == ["E501"]
    assert parsed["lint"]["isort"]["known-first-party"] == ["mdoutline"]


def test_settings_path_resolves_to_ruff_toml():
    """S2: ruff's own discovery reports ruff.toml — not pyproject.toml — as in effect."""
    ruff = find_ruff()
    proc = run([ruff, "check", "--no-cache", "--show-settings", "mdoutline.py"], cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    settings_line = next(
        (ln for ln in proc.stdout.splitlines() if ln.startswith("Settings path:")), ""
    )
    quoted = settings_line.split('"')[1] if '"' in settings_line else ""
    assert quoted == str(REPO / "ruff.toml"), (
        f"Settings path is {quoted!r}, expected the repo's ruff.toml"
    )


def test_effective_settings_match_ruff_toml():
    """S2/S3: effective settings carry ruff.toml's values (line length, target,
    isort first-party, select/ignore semantics)."""
    ruff = find_ruff()
    dump = ruff_show_settings(ruff, REPO)
    assert "Settings path:" in dump
    assert "linter.line_length = 100" in dump
    assert "linter.pycodestyle.max_line_length = 100" in dump
    assert "linter.unresolved_target_version = 3.11" in dump
    assert "formatter.unresolved_target_version = 3.11" in dump
    assert "mdoutline => Known(FirstParty)" in dump
    # select applied: representatives of every selected family are enabled
    enabled = dump[dump.index("linter.rules.enabled") : dump.index("linter.rules.should_fix")]
    for code in ("F401", "B006", "I001", "UP", "SIM"):
        assert code in enabled, f"rule family missing from enabled set: {code}"
    # ignore applied: E501 enabled by select E but removed by ignore
    assert "(E501)" not in enabled, 'E501 present in enabled rules despite ignore=["E501"]'


def test_ruff_check_and_format_clean_in_repo():
    """S3: production lint pass green on the real checkout."""
    ruff = find_ruff()
    lint = run([ruff, "check", "--no-cache", "."], cwd=REPO)
    assert lint.returncode == 0, f"ruff check failed:\n{lint.stdout}\n{lint.stderr}"
    fmt = run([ruff, "format", "--no-cache", "--check", "."], cwd=REPO)
    assert fmt.returncode == 0, f"ruff format --check failed:\n{fmt.stdout}\n{fmt.stderr}"


def test_make_lint_and_format_check_green():
    """Deployment readiness: the Makefile entry points still pass."""
    make = shutil.which("make")
    if not make:
        raise RuntimeError("make not found")
    venv_bin = str(REPO / ".venv" / "bin")
    env_path = venv_bin + os.pathsep + os.environ.get("PATH", "")
    for target in ("lint", "format-check"):
        proc = run([make, target], cwd=REPO, env_extra={"PATH": env_path})
        assert proc.returncode == 0, f"make {target} failed:\n{proc.stdout}\n{proc.stderr}"


def test_console_script_still_runs():
    """Deployment readiness: the installed CLI entry point works post-change."""
    cmd = shutil.which("mdoutline") or str(REPO / ".venv" / "bin" / "mdoutline")
    if not Path(cmd).exists() and shutil.which("mdoutline") is None:
        raise RuntimeError("mdoutline console script not found")
    proc = subprocess.run(
        [cmd], input="# Hello\n## World\n", capture_output=True, text=True, timeout=TIMEOUT_S
    )
    assert proc.returncode == 0, proc.stderr
    assert "Hello" in proc.stdout and "World" in proc.stdout


# --------------------------------------------- S3: zero behavior change


def test_settings_identical_pre_vs_post_deletion(tmp_path):
    """S3 core: full effective-settings dump identical with and without the dead block."""
    git, ruff = find_git(), find_ruff()
    pre = build_tree(git, tmp_path / "pre", pyproject_blob=parent_pyproject(git))
    post = build_tree(git, tmp_path / "post")
    assert "[tool.ruff]" in (pre / "pyproject.toml").read_text()
    assert "[tool.ruff]" not in (post / "pyproject.toml").read_text()
    dump_pre = normalize(ruff_show_settings(ruff, pre), pre)
    dump_post = normalize(ruff_show_settings(ruff, post), post)
    assert dump_pre == dump_post, "effective ruff settings differ pre vs post deletion"


def test_rule_firing_identical_pre_vs_post_deletion(tmp_path):
    """S3 core: identical violations fire on an identical probe file in both trees.

    Honesty guard: the probe asserts the expected codes actually fire (F841,
    B006, I001) and E501 stays silent — so this comparison is known-sensitive
    to any config drift, not vacuously equal on a clean file.
    """
    git, ruff = find_git(), find_ruff()
    pre = build_tree(git, tmp_path / "pre", pyproject_blob=parent_pyproject(git))
    post = build_tree(git, tmp_path / "post")
    for tree in (pre, post):
        (tree / "scratch_violations.py").write_text(VIOLATIONS_PROBE, encoding="utf-8")
    out = {}
    for name, tree in (("pre", pre), ("post", post)):
        proc = run(
            [ruff, "check", "--no-cache", "--output-format", "json", "scratch_violations.py"],
            cwd=tree,
        )
        assert proc.returncode == 1, f"{name}: expected violations, got rc={proc.returncode}"
        findings = json.loads(proc.stdout)
        codes = {f["code"] for f in findings}
        # the probe genuinely exercises the selected families
        assert "F841" in codes, f"{name}: F841 did not fire — probe not sensitive"
        assert "B006" in codes, f"{name}: B006 did not fire — probe not sensitive"
        assert "I001" in codes, f"{name}: I001 did not fire — probe not sensitive"
        assert "E501" not in codes, f"{name}: E501 fired despite ignore=[E501]"
        out[name] = sorted(
            (f["code"], f["location"]["row"], f["end_location"]["row"]) for f in findings
        )
    assert out["pre"] == out["post"], f"rule firing differs: pre={out['pre']} post={out['post']}"


def test_format_behavior_identical_pre_vs_post_deletion(tmp_path):
    """S3: formatter decisions identical in both trees on a misformatted probe."""
    git, ruff = find_git(), find_ruff()
    pre = build_tree(git, tmp_path / "pre", pyproject_blob=parent_pyproject(git))
    post = build_tree(git, tmp_path / "post")
    diffs = {}
    for name, tree in (("pre", pre), ("post", post)):
        (tree / "scratch_fmt.py").write_text(FORMAT_PROBE, encoding="utf-8")
        proc = run([ruff, "format", "--no-cache", "--check", "--diff", "scratch_fmt.py"], cwd=tree)
        assert proc.returncode == 1, f"{name}: format probe unexpectedly clean"
        diffs[name] = normalize(proc.stdout, tree)
    assert diffs["pre"] == diffs["post"], "formatter behavior differs pre vs post"
    assert diffs["post"].strip(), "format diff empty — probe not sensitive"


def test_mangled_ruff_block_in_pyproject_changes_nothing(tmp_path):
    """S3 deadness proof: re-adding a MANGLED [tool.ruff] block (line-length=10,
    select=["E"]) to pyproject.toml leaves effective settings byte-identical —
    proving pyproject's ruff table is dead, not merely redundant."""
    git, ruff = find_git(), find_ruff()
    mangled = (
        parent_pyproject(git)
        .replace("line-length = 100", "line-length = 10")
        .replace('select = ["E", "F", "W", "I", "UP", "B", "SIM"]', 'select = ["E"]')
    )
    assert "line-length = 10" in mangled and 'select = ["E"]' in mangled
    mangle_tree = build_tree(git, tmp_path / "mangled", pyproject_blob=mangled)
    plain_tree = build_tree(git, tmp_path / "plain")
    dump_mangled = normalize(ruff_show_settings(ruff, mangle_tree), mangle_tree)
    dump_plain = normalize(ruff_show_settings(ruff, plain_tree), plain_tree)
    assert dump_mangled == dump_plain, (
        "mangled [tool.ruff] block changed effective settings — block is NOT dead"
    )
    assert "linter.line_length = 100" in dump_plain
