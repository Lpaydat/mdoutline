"""Behavior tests for mdoutline ticket-01 (integration verification).

Every test asserts user-visible behavior derived from the ticket-01 spec:
CLI subprocess probes (stdout/stderr/exit code) plus library calls through
the public module interface. No implementation details are tested.

Known, bead-tracked divergences from CommonMark are deliberately NOT asserted
here (mdoutline-3o7 glued trailing '#', ijd tab separator, zpw loose fence
closers, c8r '-' stdin alias) — this file locks the ticket-01 contract only.
"""

import os
import subprocess
import sys

import mdoutline

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(args=None, input_data=None, cwd=None):
    """Run mdoutline via subprocess; return the CompletedProcess."""
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT
    cmd = [sys.executable, "-m", "mdoutline"]
    if args is not None:
        cmd.extend(args)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else REPO_ROOT,
        env=env,
        input=input_data,
        capture_output=True,
        timeout=120,
    )


def write_file(tmp_path, name, content):
    """Write text (or bytes) to tmp_path/name and return the path."""
    path = tmp_path / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# AC: file argument prints bullets, 2-space indent per depth, h1 at column 0,
# '#' marks stripped
# ---------------------------------------------------------------------------


def test_file_argument_full_skeleton(tmp_path):
    """mdoutline FILE prints each heading as '- text', 2 spaces per depth below h1."""
    doc = "# Title\n## Section 1\n### Subsection 1.1\n#### Level4\n##### Level5\n###### Level6\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == (
        "- Title\n"
        "  - Section 1\n"
        "    - Subsection 1.1\n"
        "      - Level4\n"
        "        - Level5\n"
        "          - Level6\n"
    )
    assert result.stderr.decode() == ""


def test_file_argument_hash_marks_stripped_from_output(tmp_path):
    """Leading '#' marks are stripped; only space-preceded trailing '#' runs go."""
    doc = "# Alpha\n## Beta #trailer\n#### Gamma\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Alpha\n  - Beta #trailer\n      - Gamma\n"


def test_indent_is_purely_depth_based_no_normalization(tmp_path):
    """A deep heading with no ancestors still indents by its own depth."""
    doc = "### Orphan h3\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "    - Orphan h3\n"


def test_internal_hashes_preserved_in_text(tmp_path):
    """'#' inside heading text (not trailing sequence) survives rendering."""
    doc = "# Chapter #1: Intro\n## The # tag\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Chapter #1: Intro\n  - The # tag\n"


# ---------------------------------------------------------------------------
# AC: fence handling (backtick + tilde, indented openers, unclosed at EOF)
# ---------------------------------------------------------------------------


def test_backtick_fence_suppresses_headings_end_to_end(tmp_path):
    """'#' lines inside a backtick fence are not listed; before/after are."""
    doc = "# Before\n```\n# Hidden\n## Also hidden\n```\n# After\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Before\n- After\n"


def test_tilde_fence_suppresses_headings_end_to_end(tmp_path):
    """'#' lines inside a tilde fence are not listed."""
    doc = "# Before\n~~~\n# Hidden\n~~~\n# After\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Before\n- After\n"


def test_fence_with_info_string_opens_fence(tmp_path):
    """A fence opener may carry an info string (```python); it still fences."""
    doc = "# Before\n```python\n# Hidden\n```\n# After\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Before\n- After\n"


def test_indented_fence_openers_up_to_three_spaces(tmp_path):
    """Fence openers indented 1-3 spaces still open (and close) fences."""
    doc = "# A\n ```\n# Hidden1\n ```\n# B\n  ~~~\n# Hidden2\n  ~~~\n# C\n   ```\n# Hidden3\n   ```\n# D\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- A\n- B\n- C\n- D\n"


def test_unclosed_fence_at_eof_suppresses_to_end(tmp_path):
    """An unclosed fence at EOF suppresses every heading to end of file."""
    doc = "# Before\n```\n# Hidden1\n## Hidden2\n\n# Still hidden\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Before\n"


def test_unclosed_tilde_fence_at_eof_suppresses_to_end(tmp_path):
    """An unclosed tilde fence at EOF suppresses headings to end of file."""
    doc = "# Before\n~~~\n# Hidden\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Before\n"


def test_mixed_fence_chars_do_not_close():
    """A tilde line does not close a backtick fence, and vice versa."""
    lines = ["# A", "```", "# H1", "~~~", "# H2", "```", "# B", "~~~", "# H3", "~~~", "# C"]
    assert mdoutline.extract_headings(lines) == [(1, "A"), (1, "B"), (1, "C")]


def test_four_backticks_open_and_three_do_not_close_is_known_divergence():
    """Spec-canonical fences are exactly 3+ matching chars; asserting only
    the spec-guaranteed direction: an equal-length closer closes the fence."""
    lines = ["# A", "````", "# Hidden", "````", "# B"]
    assert mdoutline.extract_headings(lines) == [(1, "A"), (1, "B")]


# ---------------------------------------------------------------------------
# AC: depth parsing — 1-6 hashes, 7+ not; <= 3 leading spaces is, 4+ is not
# ---------------------------------------------------------------------------


def test_depths_one_through_six_all_recognized(tmp_path):
    """Exactly 1-6 leading '#' produce headings of that depth."""
    doc = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == (
        "- H1\n  - H2\n    - H3\n      - H4\n        - H5\n          - H6\n"
    )


def test_seven_hashes_is_not_a_heading(tmp_path):
    """Seven or more '#' are not a heading (7, 8, 12 hashes probed)."""
    doc = "# Real\n####### Seven\n######## Eight\n############ Twelve\n## Real2\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Real\n  - Real2\n"


def test_leading_spaces_one_two_three_are_headings(tmp_path):
    """1-3 leading spaces before '#' still yield a heading."""
    doc = "# A\n # B\n  # C\n   # D\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- A\n- B\n- C\n- D\n"


def test_four_plus_leading_spaces_not_a_heading(tmp_path):
    """4, 5, and 40 leading spaces disqualify the heading."""
    doc = "# A\n    # no1\n     # no2\n" + (" " * 40) + "# no3\n## B\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- A\n  - B\n"


def test_hash_then_space_or_eol_required(tmp_path):
    """'#' must be followed by a space or end of line: '#tag' is not a heading,
    bare '#' is (empty text)."""
    doc = "# Real\n#nospace\n##also\n###### six ok\n# bare\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- Real\n          - six ok\n- bare\n"


# ---------------------------------------------------------------------------
# AC: trailing closing '#'s stripped ('## Title ##' -> 'Title')
# ---------------------------------------------------------------------------


def test_trailing_closing_hashes_stripped(tmp_path):
    """A space-separated trailing '#' sequence is removed from heading text."""
    doc = "## Title ##\n### Header ###\n###### Deep ######\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "  - Title\n    - Header\n          - Deep\n"


def test_trailing_hashes_with_gap_whitespace_stripped(tmp_path):
    """Whitespace between text and the closing '#' run is also stripped."""
    doc = "## Title   ##\n### Header\t###\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "  - Title\n    - Header\n"


# ---------------------------------------------------------------------------
# AC: stdin mode, error contract, empty inputs
# ---------------------------------------------------------------------------


def test_stdin_mode_same_output_as_file(tmp_path):
    """No file argument reads stdin; output is byte-identical to file mode."""
    doc = (
        "# Title\n"
        "## Section 1\n"
        "### Subsection 1.1\n"
        "## Section 2\n"
        "#### Deep\n"
        "``` \n# hidden in fence\n```\n"
        "##### Five\n"
    )
    path = write_file(tmp_path, "doc.md", doc)
    via_file = run_cli([str(path)])
    via_stdin = run_cli(input_data=doc.encode("utf-8"))

    assert via_stdin.returncode == 0
    assert via_stdin.stderr.decode() == ""
    assert via_stdin.stdout == via_file.stdout
    assert via_stdin.stdout.decode() == (
        "- Title\n"
        "  - Section 1\n"
        "    - Subsection 1.1\n"
        "  - Section 2\n"
        "      - Deep\n"
        "        - Five\n"
    )


def test_missing_file_error_contract(tmp_path):
    """Missing file: non-empty stderr naming the file, exit code 1, no traceback."""
    result = run_cli([str(tmp_path / "definitely_missing.md")])

    assert result.returncode == 1
    stderr = result.stderr.decode()
    assert stderr != ""
    assert "definitely_missing.md" in stderr
    assert "Traceback" not in stderr
    assert result.stdout.decode() == ""


def test_normal_runs_exit_zero(tmp_path):
    """Ordinary successful runs (file with headings, file without) exit 0."""
    with_headings = write_file(tmp_path, "a.md", "# X\n")
    without = write_file(tmp_path, "b.md", "no headings here\n")
    assert run_cli([str(with_headings)]).returncode == 0
    assert run_cli([str(without)]).returncode == 0


def test_empty_file_empty_stdout_exit_zero(tmp_path):
    """A completely empty file produces empty stdout and exit 0."""
    path = write_file(tmp_path, "empty.md", "")
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == ""
    assert result.stderr.decode() == ""


def test_file_with_no_headings_empty_stdout_exit_zero(tmp_path):
    """Prose-only file produces empty stdout and exit 0."""
    path = write_file(tmp_path, "prose.md", "Just text\nMore text\na # not a heading\n")
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == ""
    assert result.stderr.decode() == ""


def test_empty_stdin_empty_stdout_exit_zero():
    """Zero-byte stdin produces empty stdout and exit 0."""
    result = run_cli(input_data=b"")

    assert result.returncode == 0
    assert result.stdout.decode() == ""
    assert result.stderr.decode() == ""


# ---------------------------------------------------------------------------
# Library-level behavior (public functions of the single-module contract)
# ---------------------------------------------------------------------------


def test_extract_headings_empty_list():
    """extract_headings([]) returns []."""
    assert mdoutline.extract_headings([]) == []


def test_extract_headings_generator_input():
    """extract_headings accepts any iterable of lines (generator probed)."""
    lines = (line for line in ["# One", "## Two", "```", "# Hidden", "```"])
    assert mdoutline.extract_headings(lines) == [(1, "One"), (2, "Two")]


def test_extract_headings_returns_depth_text_tuples():
    """Return shape is (depth, text) with depth 1-6 and stripped text."""
    result = mdoutline.extract_headings(["#  Spaced  ", "##\tTabbed text"])
    assert result[0] == (1, "Spaced")
    assert isinstance(result[0][0], int)
    assert isinstance(result[0][1], str)


def test_render_outline_two_space_indent_per_depth():
    """render_outline indents 2 spaces per depth below h1; h1 at column 0."""
    headings = [(1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, "e"), (6, "f")]
    assert mdoutline.render_outline(headings) == (
        "- a\n  - b\n    - c\n      - d\n        - e\n          - f\n"
    )


def test_render_outline_empty_list_empty_string():
    """render_outline([]) returns '' (no newline)."""
    assert mdoutline.render_outline([]) == ""


def test_render_outline_ends_with_single_newline():
    """Non-empty outline ends with exactly one newline."""
    out = mdoutline.render_outline([(1, "x"), (2, "y")])
    assert out.endswith("\n")
    assert not out.endswith("\n\n")


def test_render_outline_bare_hash_renders_lone_dash():
    """A heading with empty text renders as a lone '-' with no trailing space."""
    assert mdoutline.render_outline([(2, "")]) == "  -\n"


# ---------------------------------------------------------------------------
# Attack phase: adversarial and deployment-readiness probes
# ---------------------------------------------------------------------------


def test_setext_headings_not_recognized(tmp_path):
    """Spec: Setext headings are NOT recognized — underlines are plain text."""
    doc = "Title\n=====\n\nSubtitle\n-----\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == ""


def test_crlf_line_endings_file_and_stdin(tmp_path):
    """CRLF input (file and stdin) yields the same outline as LF."""
    doc = "# A\r\n## B\r\n### C\r\n"
    path = write_file(tmp_path, "crlf.md", doc.encode("utf-8"))
    expected = "- A\n  - B\n    - C\n"

    via_file = run_cli([str(path)])
    via_stdin = run_cli(input_data=doc.encode("utf-8"))

    assert via_file.returncode == 0
    assert via_file.stdout.decode() == expected
    assert via_stdin.returncode == 0
    assert via_stdin.stdout.decode() == expected


def test_bom_does_not_swallow_first_heading(tmp_path):
    """A UTF-8 BOM (file and stdin) does not hide the first heading."""
    bom_doc = b"\xef\xbb\xbf# First\n## Second\n"
    path = write_file(tmp_path, "bom.md", bom_doc)
    expected = "- First\n  - Second\n"

    via_file = run_cli([str(path)])
    via_stdin = run_cli(input_data=bom_doc)

    assert via_file.returncode == 0
    assert via_file.stdout.decode() == expected
    assert via_stdin.returncode == 0
    assert via_stdin.stdout.decode() == expected


def test_unicode_heading_text_round_trips(tmp_path):
    """Non-ASCII heading text survives to stdout byte-for-byte (UTF-8)."""
    text = "Überschrift — ✓ 中文 🚀"
    path = write_file(tmp_path, "uni.md", f"# {text}\n")
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode("utf-8") == f"- {text}\n"


def test_directory_argument_clean_error(tmp_path):
    """A directory as the file argument: exit 1, clean stderr, no traceback."""
    result = run_cli([str(tmp_path)])

    assert result.returncode == 1
    stderr = result.stderr.decode()
    assert "cannot read" in stderr
    assert "Traceback" not in stderr
    assert result.stdout.decode() == ""


def test_unreadable_file_clean_error(tmp_path):
    """A chmod-000 file: exit 1, clean stderr, no traceback (skipped as root)."""
    if os.geteuid() == 0:
        import pytest

        pytest.skip("permission bits meaningless as root")
    path = write_file(tmp_path, "secret.md", "# secret\n")
    os.chmod(path, 0o000)
    result = run_cli([str(path)])

    assert result.returncode == 1
    stderr = result.stderr.decode()
    assert "cannot read" in stderr
    assert "Traceback" not in stderr


def test_invalid_utf8_file_clean_error(tmp_path):
    """Invalid UTF-8 in the file argument: exit 1, clean stderr, no traceback."""
    path = write_file(tmp_path, "bad.md", b"# ok\n\xff\xfe\x00\n")
    result = run_cli([str(path)])

    assert result.returncode == 1
    stderr = result.stderr.decode()
    assert stderr != ""
    assert "Traceback" not in stderr


def test_invalid_utf8_stdin_clean_error():
    """Invalid UTF-8 on stdin: exit 1, stderr names stdin, no traceback."""
    result = run_cli(input_data=b"\xff\xfe\x00\x00")

    assert result.returncode == 1
    stderr = result.stderr.decode()
    assert "stdin" in stderr.lower()
    assert "None" not in stderr
    assert "Traceback" not in stderr


def test_closed_stdin_clean_error(tmp_path):
    """stdin closed (fd 0 closed, as in `mdoutline 0<&-`): exit 1, one-line
    error, no traceback."""
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT
    script = f"cd {tmp_path} && PYTHONPATH={REPO_ROOT} {sys.executable} -m mdoutline 0<&-"
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=120)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr != ""
    assert "Traceback" not in result.stderr
    assert len(result.stderr.strip().splitlines()) == 1


def test_empty_string_argument_is_missing_file():
    """An empty-string argument is a (missing) filename: exit 1, clean error."""
    result = run_cli([""])

    assert result.returncode == 1
    stderr = result.stderr.decode()
    assert "cannot read" in stderr.lower()
    assert "Traceback" not in stderr


def test_extra_positional_arguments_rejected():
    """Two file arguments: argparse usage error (exit 2), no traceback."""
    result = run_cli(["one.md", "two.md"])

    assert result.returncode == 2
    stderr = result.stderr.decode()
    assert "usage" in stderr.lower()
    assert "Traceback" not in stderr


def test_help_exits_zero_with_usage():
    """--help prints usage and exits 0."""
    result = run_cli(["--help"])

    assert result.returncode == 0
    assert b"usage" in result.stdout.lower()


def test_relative_path_resolved_from_cwd(tmp_path):
    """A relative file argument resolves against the process cwd."""
    path = write_file(tmp_path, "notes.md", "# Relative OK\n")
    result = run_cli(["notes.md"], cwd=tmp_path)

    assert result.returncode == 0
    assert result.stdout.decode() == "- Relative OK\n"
    assert path.exists()


def test_large_input_20k_headings(tmp_path):
    """20k headings through stdin: exit 0, all lines present, bounded time."""
    doc = "".join(f"# H{i}\n## S{i}\n" for i in range(10000))
    result = run_cli(input_data=doc.encode("utf-8"))

    assert result.returncode == 0
    lines = result.stdout.decode().splitlines()
    assert len(lines) == 20000
    assert lines[0] == "- H0"
    assert lines[-1] == "  - S9999"


def test_broken_pipe_no_traceback_and_consumer_gets_lines(tmp_path):
    """`mdoutline | head -1`: consumer sees the first line; mdoutline's stderr
    carries no traceback and no BrokenPipeError noise."""
    env = os.environ.copy()
    env["PYTHONPATH"] = REPO_ROOT
    doc = "".join(f"# H{i}\n" for i in range(20000))
    result = subprocess.run(
        f"{sys.executable} -m mdoutline | head -1",
        shell=True,
        cwd=str(tmp_path),
        env=env,
        input=doc.encode("utf-8"),
        capture_output=True,
        timeout=120,
    )

    assert result.stdout.decode() == "- H0\n"
    assert "Traceback" not in result.stderr.decode()
    assert "BrokenPipeError" not in result.stderr.decode()


def test_heading_detection_ignores_hash_embedded_in_prose(tmp_path):
    """A '#' run in the middle of a prose line is never a heading."""
    doc = "We use #### style markers mid-sentence\nand # signs everywhere #\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == ""


def test_fence_state_survives_blank_lines_and_prose(tmp_path):
    """Blank lines and prose inside an open fence do not close it."""
    doc = "# A\n```\n\nsome code\n\n# Hidden\n```\n# B\n"
    path = write_file(tmp_path, "doc.md", doc)
    result = run_cli([str(path)])

    assert result.returncode == 0
    assert result.stdout.decode() == "- A\n- B\n"
