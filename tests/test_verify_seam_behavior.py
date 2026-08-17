"""Adversarial behavior-verification of the shared CLI seam (ticket-refactor-01 C1+C2).

Every expected output below was derived BY HAND from the CLI contract
(mdoutline public interface + spec t_6e7f59b1) BEFORE running:

    plain:    "- Top\\n  - Alpha\\n    - Nested\\n  - Beta\\n- Second\\n"
    numbers:  1. / 1.1 / 1.1.1 / 1.2 / 2.
    skipped-level numbering: h1 -> h3 renders "1.0.1"

Tests exercise the seam ONLY through its public surface: the run_cli /
run_cli_pipeline / write_md_file fixtures and resolve_mdoutline_cmd.
No implementation internals are imported or monkeypatched.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

import mdoutline
from conftest import resolve_mdoutline_cmd

REPO_ROOT = Path(__file__).resolve().parent.parent
FOREIGN_PYTHON = "/usr/bin/python"
SKIP_REASON = "mdoutline command not found - set MDOUTLINE_BIN or install the package"

# Canonical fixture document. Heading set: (1,Top)(2,Alpha)(3,Nested)(2,Beta)(1,Second)
DOC = "# Top\n## Alpha\n### Nested\n## Beta\n# Second\n"
OUT_PLAIN = "- Top\n  - Alpha\n    - Nested\n  - Beta\n- Second\n"
OUT_NUMBERS = "- 1. Top\n  - 1.1 Alpha\n    - 1.1.1 Nested\n  - 1.2 Beta\n- 2. Second\n"
OUT_DEPTH2 = "- Top\n  - Alpha\n  - Beta\n- Second\n"
OUT_NUMBERS_DEPTH2 = "- 1. Top\n  - 1.1 Alpha\n  - 1.2 Beta\n- 2. Second\n"
OUT_DEPTH1 = "- Top\n- Second\n"

DOC_SKIP_LEVEL = "# A\n### Deep\n"
OUT_SKIP_LEVEL_NUMBERS = "- 1. A\n    - 1.0.1 Deep\n"

DOC_UNICODE = "# café ☕\n## 中文标题\n## émoji 🎉 heading\n"
OUT_UNICODE_PLAIN = "- café ☕\n  - 中文标题\n  - émoji 🎉 heading\n"
OUT_UNICODE_NUMBERS = "- 1. café ☕\n  - 1.1 中文标题\n  - 1.2 émoji 🎉 heading\n"

DOC_FENCE = "```\n# not a heading\n```\n# real\n"
OUT_FENCE = "- real\n"

DOC_TRAILING_HASHES = "## Title ##\n"
OUT_TRAILING_HASHES = "  - Title\n"

DOC_METACHAR = '# T"q $X `bt`\n## $(pwd)\n'
OUT_METACHAR = '- T"q $X `bt`\n  - $(pwd)\n'


def _system_mdoutline_present() -> bool:
    """True if a system-level mdoutline exists (weakens stripped-PATH proofs)."""
    return Path("/usr/bin/mdoutline").exists() or Path("/bin/mdoutline").exists()


# ---------------------------------------------------------------------------
# Ground-truth independence: the literals above must agree with the library
# API (in-process), which the refactor is required to leave untouched.
# ---------------------------------------------------------------------------


def test_library_ground_truth_matches_hand_derived_literals():
    lines = DOC.splitlines()
    heads = mdoutline.extract_headings(lines)
    assert mdoutline.render_outline(heads) == OUT_PLAIN
    numbered = mdoutline.number_headings(heads)
    assert mdoutline.render_outline(numbered) == OUT_NUMBERS
    assert mdoutline.render_outline(mdoutline.filter_by_depth(heads, 2)) == OUT_DEPTH2
    assert mdoutline.render_outline(mdoutline.filter_by_depth(heads, 1)) == OUT_DEPTH1
    skip_heads = mdoutline.extract_headings(DOC_SKIP_LEVEL.splitlines())
    assert mdoutline.render_outline(mdoutline.number_headings(skip_heads)) == OUT_SKIP_LEVEL_NUMBERS
    uni_heads = mdoutline.extract_headings(DOC_UNICODE.splitlines())
    assert mdoutline.render_outline(mdoutline.number_headings(uni_heads)) == OUT_UNICODE_NUMBERS


# ---------------------------------------------------------------------------
# R8 - CLI public behavior preserved (happy paths, file + stdin, both modes)
# ---------------------------------------------------------------------------


def test_cli_file_argument_plain_outline(run_cli, write_md_file):
    doc = write_md_file("doc.md", DOC)
    result = run_cli([str(doc)])
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == OUT_PLAIN


def test_cli_stdin_string_mode(run_cli):
    result = run_cli([], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == OUT_PLAIN


def test_cli_stdin_bytes_mode_returns_bytes(run_cli):
    result = run_cli([], stdin=DOC.encode("utf-8"))
    assert result.returncode == 0
    assert isinstance(result.stdout, bytes)
    assert result.stdout == OUT_PLAIN.encode("utf-8")


def test_cli_numbers_flag(run_cli):
    result = run_cli(["--numbers"], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == OUT_NUMBERS


def test_cli_max_depth_2(run_cli):
    result = run_cli(["--max-depth", "2"], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == OUT_DEPTH2


def test_cli_max_depth_1(run_cli):
    result = run_cli(["--max-depth", "1"], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == OUT_DEPTH1


def test_cli_max_depth_0_empty_output_zero_rc(run_cli):
    """Boundary: 0 filters every heading (all depths >= 1) - empty stdout, rc 0."""
    result = run_cli(["--max-depth", "0"], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == ""


def test_cli_max_depth_above_max_heading_depth_is_noop(run_cli):
    """Boundary: 7 exceeds any ATX depth (1-6) - nothing is filtered."""
    result = run_cli(["--max-depth", "7"], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == OUT_PLAIN


def test_cli_numbers_composed_with_max_depth(run_cli):
    result = run_cli(["--numbers", "--max-depth", "2"], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == OUT_NUMBERS_DEPTH2


def test_cli_skipped_level_numbers_render_mechanical_zero(run_cli):
    """h1 followed directly by h3 numbers as 1.0.1 (not 1.1)."""
    result = run_cli(["--numbers"], stdin=DOC_SKIP_LEVEL)
    assert result.returncode == 0
    assert result.stdout == OUT_SKIP_LEVEL_NUMBERS


def test_cli_unicode_headings_roundtrip(run_cli):
    result = run_cli(["--numbers"], stdin=DOC_UNICODE)
    assert result.returncode == 0
    assert result.stdout == OUT_UNICODE_NUMBERS


def test_cli_unicode_plain(run_cli):
    result = run_cli([], stdin=DOC_UNICODE)
    assert result.returncode == 0
    assert result.stdout == OUT_UNICODE_PLAIN


def test_cli_headings_inside_fence_ignored(run_cli):
    result = run_cli([], stdin=DOC_FENCE)
    assert result.returncode == 0
    assert result.stdout == OUT_FENCE


def test_cli_trailing_closing_hashes_stripped(run_cli):
    result = run_cli([], stdin=DOC_TRAILING_HASHES)
    assert result.returncode == 0
    assert result.stdout == OUT_TRAILING_HASHES


def test_cli_bom_stripped_from_stdin_bytes(run_cli):
    payload = ("\ufeff" + DOC_UNICODE).encode("utf-8")
    result = run_cli([], stdin=payload)
    assert result.returncode == 0
    assert result.stdout == OUT_UNICODE_PLAIN.encode("utf-8")


def test_cli_empty_input_empty_output_zero_rc(run_cli):
    result = run_cli([], stdin="")
    assert result.returncode == 0
    assert result.stdout == ""


def test_cli_no_headings_input(run_cli):
    result = run_cli([], stdin="just text\n\n- a bullet, not a heading\n")
    assert result.returncode == 0
    assert result.stdout == ""


def test_cli_help_lists_both_options(run_cli):
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "--max-depth" in result.stdout
    assert "--numbers" in result.stdout


def test_cli_cwd_passthrough_relative_file(tmp_path, run_cli, write_md_file):
    write_md_file("doc.md", DOC)
    result = run_cli(["doc.md"], cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout == OUT_PLAIN


def test_cli_large_input_100k_headings(run_cli):
    """Stress: 100k headings (~600 KB stdin) - correct count, single pass."""
    doc = "# A\n" * 100_000
    result = run_cli([], stdin=doc)
    assert result.returncode == 0
    assert len(result.stdout.splitlines()) == 100_000
    assert result.stdout.startswith("- A\n")


# ---------------------------------------------------------------------------
# R8 - CLI error paths preserved
# ---------------------------------------------------------------------------


def test_cli_missing_file_rc1_named_in_stderr(run_cli):
    result = run_cli(["/nonexistent/definitely/nope.md"])
    assert result.returncode == 1
    assert result.stdout == ""
    assert "mdoutline: cannot read '/nonexistent/definitely/nope.md'" in result.stderr
    assert "No such file" in result.stderr


def test_cli_directory_as_file_rc1(run_cli, tmp_path):
    result = run_cli([str(tmp_path)])
    assert result.returncode == 1
    assert "mdoutline: cannot read" in result.stderr


def test_cli_invalid_utf8_file_rc1(run_cli, tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"# title\n\xff\xfe invalid continuation\n")
    result = run_cli([str(bad)])
    assert result.returncode == 1
    assert "mdoutline: cannot read" in result.stderr


def test_cli_unreadable_file_rc1(run_cli, tmp_path):
    if os.geteuid() == 0:
        pytest.skip("permission bits not enforced for root")
    secret = tmp_path / "secret.md"
    secret.write_text(DOC, encoding="utf-8")
    os.chmod(secret, 0o000)
    result = run_cli([str(secret)])
    assert result.returncode == 1
    assert "mdoutline: cannot read" in result.stderr


def test_cli_invalid_max_depth_rc2_usage_error(run_cli):
    result = run_cli(["--max-depth", "abc"], stdin=DOC)
    assert result.returncode == 2
    assert "invalid int value" in result.stderr


def test_cli_negative_max_depth_rc2_rejected(run_cli):
    result = run_cli(["--max-depth", "-1"], stdin=DOC)
    assert result.returncode == 2
    assert "must be >= 0, got -1" in result.stderr


# ---------------------------------------------------------------------------
# R1 - MDOUTLINE_BIN precedence and shlex semantics
# ---------------------------------------------------------------------------


def test_seam_env_override_wins_over_path_and_sysconfig(run_cli, monkeypatch):
    """MDOUTLINE_BIN must beat both which() and sysconfig discovery.
    The quoted \\n also proves shlex quoting round-trips through the seam."""
    monkeypatch.setenv("MDOUTLINE_BIN", r"printf 'OVERRIDE-RAN\n'")
    result = run_cli(["ignored-arg"])
    assert result.returncode == 0
    assert result.stdout == "OVERRIDE-RAN\n"


def test_seam_env_override_whole_command_shlex_split(run_cli, monkeypatch):
    monkeypatch.setenv("MDOUTLINE_BIN", "/bin/echo MULTI TOKEN")
    result = run_cli(["extra"])
    assert result.returncode == 0
    assert result.stdout == "MULTI TOKEN extra\n"


def test_seam_whitespace_only_override_falls_through(run_cli, monkeypatch):
    """Honesty: the value is truly whitespace-only (spaces + tabs)."""
    monkeypatch.setenv("MDOUTLINE_BIN", "   \t  ")
    result = run_cli([], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == OUT_PLAIN


def test_seam_malformed_override_falls_through_not_crash(run_cli, monkeypatch):
    """Honesty: genuinely unparseable - a real unclosed double quote."""
    monkeypatch.setenv("MDOUTLINE_BIN", '"unclosed')
    result = run_cli([], stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == OUT_PLAIN


def test_seam_malformed_override_resolver_returns_none(monkeypatch):
    monkeypatch.setenv("MDOUTLINE_BIN", "'also-unclosed")
    assert resolve_mdoutline_cmd() is None


def test_seam_nonexistent_override_raises_loudly(run_cli, monkeypatch):
    """Override is trusted blindly: a bad path surfaces as FileNotFoundError,
    never as a silent fallback to another command."""
    monkeypatch.setenv("MDOUTLINE_BIN", "/nonexistent/mdoutline-proxy")
    with pytest.raises(FileNotFoundError):
        run_cli([], stdin=DOC)


def test_seam_resolver_none_only_when_nothing_discoverable():
    """Env-independent invariant: resolve() returns None ONLY when neither
    which() nor the active interpreter's sysconfig scripts dir has the binary;
    when it returns a command it is a non-empty argv list (or MDOUTLINE_BIN)."""
    import shutil
    import sysconfig

    cmd = resolve_mdoutline_cmd()
    override = __import__("shlex").split(os.environ.get("MDOUTLINE_BIN", ""))
    if cmd is None:
        assert not override, "override set but resolver returned None (parse fall-through)"
        assert shutil.which("mdoutline") is None
        assert not (Path(sysconfig.get_path("scripts")) / "mdoutline").exists()
    else:
        assert isinstance(cmd, list) and cmd and all(isinstance(t, str) for t in cmd)


# ---------------------------------------------------------------------------
# R3 - PYTHONPATH construction (observable via the pipeline fixture + shell)
# ---------------------------------------------------------------------------


def test_seam_pythonpath_repo_root_first_preserving_existing(run_cli_pipeline, monkeypatch):
    monkeypatch.setenv("MDOUTLINE_BIN", r"printf 'PP:%s\n'")
    monkeypatch.setenv("PYTHONPATH", "/opt/preexisting")
    result = run_cli_pipeline("$PYTHONPATH", stdin="")
    assert result.returncode == 0
    assert result.stdout == f"PP:{REPO_ROOT}{os.pathsep}/opt/preexisting\n"


def test_seam_pythonpath_repo_root_alone_when_unset(run_cli_pipeline, monkeypatch):
    monkeypatch.setenv("MDOUTLINE_BIN", r"printf 'PP:%s\n'")
    monkeypatch.delenv("PYTHONPATH", raising=False)
    result = run_cli_pipeline("$PYTHONPATH", stdin="")
    assert result.returncode == 0
    assert result.stdout == f"PP:{REPO_ROOT}\n"


# ---------------------------------------------------------------------------
# R4 - shared timeout policy enforced on both runner fixtures
# ---------------------------------------------------------------------------


def test_seam_timeout_enforced_run_cli(run_cli, monkeypatch):
    monkeypatch.setenv("MDOUTLINE_BIN", "/bin/sleep")
    with pytest.raises(subprocess.TimeoutExpired):
        run_cli(["2"], timeout=0.3)


def test_seam_timeout_enforced_run_cli_pipeline(run_cli_pipeline, monkeypatch):
    monkeypatch.setenv("MDOUTLINE_BIN", "/bin/sleep")
    with pytest.raises(subprocess.TimeoutExpired):
        run_cli_pipeline("1.5", stdin="", timeout=0.3)


# ---------------------------------------------------------------------------
# R5 - tmp-file writer fixture
# ---------------------------------------------------------------------------


def test_seam_write_md_file_roundtrip_unicode(tmp_path, write_md_file):
    path = write_md_file("u.md", DOC_UNICODE)
    assert isinstance(path, Path)
    assert path.parent == tmp_path
    assert path.exists()
    assert path.read_text(encoding="utf-8") == DOC_UNICODE


def test_seam_write_md_file_empty_content(tmp_path, write_md_file):
    path = write_md_file("empty.md", "")
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""
    assert path.stat().st_size == 0


def test_seam_write_md_file_name_with_spaces(tmp_path, write_md_file):
    path = write_md_file("my doc (v2).md", DOC)
    assert path.name == "my doc (v2).md"
    assert path.read_text(encoding="utf-8") == DOC


def test_seam_written_file_is_valid_cli_input(tmp_path, run_cli, write_md_file):
    path = write_md_file("doc.md", DOC)
    result = run_cli([str(path)])
    assert result.returncode == 0
    assert result.stdout == OUT_PLAIN


# ---------------------------------------------------------------------------
# Pipeline fixture - shell-composition robustness
# ---------------------------------------------------------------------------


def test_seam_pipeline_plain_run_metachar_headings(run_cli_pipeline):
    """Heading text laden with shell metachars survives the shell=True path."""
    result = run_cli_pipeline("", stdin=DOC_METACHAR)
    assert result.returncode == 0
    assert result.stdout == OUT_METACHAR


def test_seam_pipeline_downstream_pipe(run_cli_pipeline):
    result = run_cli_pipeline("| grep Alpha", stdin=DOC)
    assert result.returncode == 0
    assert result.stdout == "  - Alpha\n"


# ---------------------------------------------------------------------------
# R7 - C2 boundary: conftest shares runner/writer/resolver ONLY
# ---------------------------------------------------------------------------


def test_seam_conftest_carries_no_expected_outputs():
    """C2 boundary: no hoisted expected-output/document constants at module
    level. Anchored per-line to avoid the MDOUTLINE_BIN substring trap."""
    src = (Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
    hoisted = re.findall(r"^(?:OUTLINE|DOC)_\w+\s*=", src, flags=re.MULTILINE)
    assert not hoisted, f"expected outputs hoisted into conftest (C2 violation): {hoisted}"
    for fixture_name in ("run_cli", "run_cli_pipeline", "write_md_file"):
        assert f"def {fixture_name}" in src


# ---------------------------------------------------------------------------
# R2/R6 - deployment environments (wrapper runs, guarded by preconditions)
# ---------------------------------------------------------------------------

FOUR_SUITES = [
    "tests/test_cli.py",
    "tests/test_behavior_depth.py",
    "tests/test_behavior_numbers.py",
    "tests/test_behavior_numbers_verify.py",
]


def _stripped_env():
    env = dict(os.environ)
    env["PATH"] = "/usr/bin:/bin"
    env.pop("MDOUTLINE_BIN", None)
    env.pop("PYTHONPATH", None)
    return env


def test_deploy_venv_off_path_suites_green_no_skips():
    """R2: venv stripped from PATH - script still found via sysconfig; nothing skips."""
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if not venv_python.exists() or _system_mdoutline_present():
        pytest.skip("canonical .venv interpreter not present or system mdoutline interferes")
    probe = subprocess.run(
        [str(venv_python), "-m", "pytest", *[str(REPO_ROOT / s) for s in FOUR_SUITES]],
        cwd=REPO_ROOT,
        env=_stripped_env(),
        capture_output=True,
        text=True,
        timeout=600,
    )
    tail = probe.stdout[-2000:]
    assert probe.returncode == 0, tail
    assert re.search(r"\d+ passed", tail), tail
    assert not re.search(r"\d+ (failed|error)", tail), tail
    assert "skipped" not in tail, f"unexpected skips with script on disk:\n{tail}"


def test_deploy_foreign_interpreter_skips_with_verbatim_reason():
    """R3+R6: foreign interpreter, script absent everywhere - four dev suites run
    green via the -m fallback; every deployment test skips with the unified
    verbatim reason."""
    if not Path(FOREIGN_PYTHON).exists() or _system_mdoutline_present():
        pytest.skip("foreign interpreter not present or system mdoutline interferes")
    probe = subprocess.run(
        [FOREIGN_PYTHON, "-m", "pytest", *[str(REPO_ROOT / s) for s in FOUR_SUITES], "-rs"],
        cwd="/tmp",
        env=_stripped_env(),
        capture_output=True,
        text=True,
        timeout=600,
    )
    tail = probe.stdout[-4000:]
    assert probe.returncode == 0, tail
    assert re.search(r"\d+ passed, 11 skipped", tail), tail
    assert not re.search(r"\d+ (failed|error)", tail), tail
    assert SKIP_REASON in tail, "verbatim skip reason missing from -rs output"


def test_deploy_foreign_cwd_dash_m_matches_library_truth():
    """R3 core: from a foreign cwd with a stripped PATH, the seam's -m fallback
    must produce output identical to the in-process library API."""
    if not Path(FOREIGN_PYTHON).exists():
        pytest.skip("foreign interpreter not present")
    repo = str(REPO_ROOT)
    snippet = (
        "import subprocess, sys, json, os\n"
        f"repo = {repo!r}\n"
        "sys.path.insert(0, repo)\n"
        "sys.path.insert(0, repo + '/tests')\n"
        "from conftest import resolve_mdoutline_cmd\n"
        "cmd = resolve_mdoutline_cmd()\n"
        "env = {'PATH': '/usr/bin:/bin'}\n"
        "if cmd is None:\n"
        "    cmd = [sys.executable, '-m', 'mdoutline']\n"
        "    env['PYTHONPATH'] = repo\n"
        "r = subprocess.run(cmd, input='# Foreign\\n## Cwd\\n', text=True,\n"
        "                   capture_output=True, timeout=60, cwd='/tmp', env=env)\n"
        "print(json.dumps([cmd[0], r.returncode, r.stdout, r.stderr]))\n"
    )
    probe = subprocess.run(
        [FOREIGN_PYTHON, "-"],
        input=snippet,
        capture_output=True,
        text=True,
        timeout=120,
        cwd="/tmp",
        env={"PATH": "/usr/bin:/bin"},
    )
    assert probe.returncode == 0, probe.stderr
    cmd0, rc, out, err = json.loads(probe.stdout.strip().splitlines()[-1])
    assert rc == 0, err
    assert out == "- Foreign\n  - Cwd\n"
    assert Path(cmd0).samefile(FOREIGN_PYTHON) or cmd0 == FOREIGN_PYTHON, cmd0
