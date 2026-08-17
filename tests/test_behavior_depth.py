"""Adversarial behavior verification for ticket-02: ``--max-depth N``.

Integration verification of depth limiting through the PUBLIC interfaces only:
  * the ``mdoutline`` console script (production entry point),
  * ``python -m mdoutline``,
  * the library API (``extract_headings`` / ``filter_by_depth`` / ``render_outline``).

Every expected output below was derived BY HAND from the spec before running:
  - ``--max-depth N`` keeps only headings with depth <= N;
  - deeper headings are dropped before rendering and survivors keep the
    indentation of their OWN depth (never re-leveled);
  - N=1 prints only h1s; N larger than the deepest heading prints everything;
  - the flag combines with stdin mode;
  - ``--max-depth`` parses an int; flag absent means no filtering.

The library is used only to assert fixture PREMISES (e.g. "this document
really contains depths 1-6"), never to compute expected output.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

from conftest import resolve_mdoutline_cmd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # library probes work without editable install

import mdoutline  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures (documents). Premise assertions live in the tests that use them.
# ---------------------------------------------------------------------------

DOC_ALL = "# Alpha\n## Beta\n### Gamma\n#### Delta\n##### Epsilon\n###### Zeta\n"
OUTLINE_ALL = "- Alpha\n  - Beta\n    - Gamma\n      - Delta\n        - Epsilon\n          - Zeta\n"

DOC_GAP = "# Root\n### Deep child\n"  # h1 then h3: re-leveling would show here

DOC_ORPHAN = "## Second\n### Third\n"  # no h1 at all

DOC_DROP = "# A\n## B\n#### C\n## D\n"  # deep heading between two same-depth

DOC_FENCE = "# Real\n```\n# Fake1\n```\n## Real2\n"

DOC_UNCLOSED_FENCE = "# Real\n```\n# Fake\n## AlsoFake\n"

DOC_TILDE_FENCE = "~~~\n# Fake\n~~~\n# Real\n"

DOC_EMPTY_TEXT = "# T\n##\n"  # second heading has empty text

DOC_TRAILING_HASHES = "## Title ##\n"

DOC_LEADING_SPACES = "   # H1\n    ## NotAHeading\n"

DOC_SEVEN_HASHES = "####### Seven\n# Real\n"

DOC_UNICODE = "# 标题 一\n### 🚀 Deep\n"

BOM_DOC = b"\xef\xbb\xbf# BOM Title\n## Deep\n"

CRLF_DOC = b"# One\r\n## Two\r\n"


def depths_of(text: str) -> list[int]:
    return [d for d, _ in mdoutline.extract_headings(text.splitlines())]


# ===========================================================================
# Phase 1 — spec matrix
# ===========================================================================


class TestKeepsDepthAtMostN:
    def test_no_flag_prints_full_outline(self, run_cli, write_md_file):
        assert depths_of(DOC_ALL) == [1, 2, 3, 4, 5, 6]  # premise: all depths exist
        r = run_cli([str(write_md_file("doc.md", DOC_ALL))])
        assert r.returncode == 0, r.stderr
        assert r.stdout == OUTLINE_ALL

    def test_no_flag_byte_identical_to_max_depth_6(self, run_cli, write_md_file):
        f = write_md_file("doc.md", DOC_ALL)
        assert run_cli([str(f)]).stdout == run_cli(["--max-depth", "6", str(f)]).stdout

    def test_max_depth_1_only_h1(self, run_cli, write_md_file):
        r = run_cli(["--max-depth", "1", str(write_md_file("doc.md", DOC_ALL))])
        assert r.returncode == 0
        assert r.stdout == "- Alpha\n"

    def test_max_depth_2_keeps_h1_h2(self, run_cli, write_md_file):
        r = run_cli(["--max-depth", "2", str(write_md_file("doc.md", DOC_ALL))])
        assert r.stdout == "- Alpha\n  - Beta\n"

    def test_max_depth_3_keeps_through_h3(self, run_cli, write_md_file):
        r = run_cli(["--max-depth", "3", str(write_md_file("doc.md", DOC_ALL))])
        assert r.stdout == "- Alpha\n  - Beta\n    - Gamma\n"

    def test_boundary_heading_depth_equal_n_is_kept(self, run_cli, write_md_file):
        # N=2 on a doc whose ONLY depth-2 heading is the boundary case.
        assert depths_of(DOC_DROP) == [1, 2, 4, 2]  # premise: an h2 exists at == N
        r = run_cli(["--max-depth", "2", str(write_md_file("doc.md", DOC_DROP))])
        assert r.stdout == "- A\n  - B\n  - D\n"  # C (h4) dropped, B/D (h2) kept

    def test_drop_is_strictly_deeper_only(self, run_cli, write_md_file):
        # N=3: everything of DOC_ALL except depths 4-6 survives.
        r = run_cli(["--max-depth", "3", str(write_md_file("doc.md", DOC_ALL))])
        assert r.stdout.count("\n") == 3


class TestN1AndOversizedN:
    def test_n1_prints_only_h1s(self, run_cli, write_md_file):
        assert depths_of(DOC_ALL) == [1, 2, 3, 4, 5, 6]
        r = run_cli(["--max-depth", "1", str(write_md_file("doc.md", DOC_ALL))])
        assert r.stdout == "- Alpha\n"  # exactly the one h1, nothing deeper

    def test_n_larger_than_deepest_prints_everything(self, run_cli, write_md_file):
        assert max(depths_of(DOC_ALL)) == 6  # premise: deepest heading is h6
        f = write_md_file("doc.md", DOC_ALL)
        assert run_cli(["--max-depth", "7", str(f)]).stdout == OUTLINE_ALL
        assert run_cli(["--max-depth", "100", str(f)]).stdout == OUTLINE_ALL

    def test_huge_integer_n_accepted(self, run_cli, write_md_file):
        # Python ints are arbitrary precision; N far beyond any heading depth
        # must still print everything (spec: "N larger than deepest").
        r = run_cli(["--max-depth", str(10**18), str(write_md_file("doc.md", DOC_ALL))])
        assert r.returncode == 0
        assert r.stdout == OUTLINE_ALL


class TestStdinModeCombines:
    def test_literal_spec_example_stdin_max_depth_1(self, run_cli):
        r = run_cli(["--max-depth", "1"], stdin=DOC_ALL.encode())
        assert r.returncode == 0, r.stderr
        assert r.stdout == b"- Alpha\n"

    def test_stdin_byte_identical_to_file_mode(self, run_cli, write_md_file):
        f = write_md_file("doc.md", DOC_ALL)
        via_stdin = run_cli(["--max-depth", "2"], stdin=DOC_ALL.encode())
        via_file = run_cli(["--max-depth", "2", str(f)])
        assert via_stdin.returncode == via_file.returncode == 0
        assert via_file.stdout.encode() == via_stdin.stdout

    def test_stdin_n0_prints_nothing_exit_0(self, run_cli):
        r = run_cli(["--max-depth", "0"], stdin=DOC_ALL.encode())
        assert r.returncode == 0
        assert r.stdout == b""


class TestIntParsing:
    def test_equals_form_matches_spaced_form(self, run_cli, write_md_file):
        f = write_md_file("doc.md", DOC_ALL)
        spaced = run_cli(["--max-depth", "3", str(f)])
        glued = run_cli(["--max-depth=3", str(f)])
        assert spaced.returncode == glued.returncode == 0
        assert spaced.stdout == glued.stdout == "- Alpha\n  - Beta\n    - Gamma\n"

    @pytest.mark.parametrize("bad", ["abc", "2.5", "", "3x", "1 2"])
    def test_non_int_values_rejected(self, run_cli, write_md_file, bad):
        r = run_cli(["--max-depth", bad, str(write_md_file("doc.md", DOC_ALL))])
        assert r.returncode == 2, (bad, r.stdout, r.stderr)
        assert r.stdout == ""
        assert "invalid int value" in r.stderr

    def test_negative_rejected_equals_form(self, run_cli, write_md_file):
        r = run_cli(["--max-depth=-1", str(write_md_file("doc.md", DOC_ALL))])
        assert r.returncode == 2
        assert "must be >= 0" in r.stderr

    def test_negative_rejected_spaced_form(self, run_cli, write_md_file):
        r = run_cli(["--max-depth", "-1", str(write_md_file("doc.md", DOC_ALL))])
        assert r.returncode == 2
        assert r.stdout == ""
        assert r.stderr != ""

    def test_missing_value_rejected(self, run_cli):
        # No flag value, no file: argparse must see a dangling --max-depth.
        r = run_cli(["--max-depth"])
        assert r.returncode == 2
        assert "expected one argument" in r.stderr

    def test_type_int_semantics_whitespace_stripped(self, run_cli, write_md_file):
        # int(" 3") == 3: the flag uses argparse int conversion, so a padded
        # value parses as 3 and behaves exactly like N=3 (AC: type=int).
        f = write_md_file("doc.md", DOC_ALL)
        padded = run_cli(["--max-depth", " 3", str(f)])
        assert padded.returncode == 0, padded.stderr
        assert padded.stdout == "- Alpha\n  - Beta\n    - Gamma\n"

    def test_duplicate_flag_last_wins(self, run_cli, write_md_file):
        f = write_md_file("doc.md", DOC_ALL)
        r = run_cli(["--max-depth", "1", "--max-depth", "3", str(f)])
        assert r.returncode == 0
        assert r.stdout == "- Alpha\n  - Beta\n    - Gamma\n"


class TestIndentNotReleveled:
    def test_gap_doc_keeps_own_depth_indent(self, run_cli, write_md_file):
        # h1 + h3: if survivors were re-leveled the h3 would get 2 spaces.
        assert depths_of(DOC_GAP) == [1, 3]
        r = run_cli(["--max-depth", "3", str(write_md_file("doc.md", DOC_GAP))])
        assert r.stdout == "- Root\n    - Deep child\n"  # 4-space indent kept

    def test_orphan_headings_not_promoted(self, run_cli, write_md_file):
        # No h1 exists; h2 must stay at 2 spaces even as the shallowest survivor.
        assert depths_of(DOC_ORPHAN) == [2, 3]
        r = run_cli(["--max-depth", "3", str(write_md_file("doc.md", DOC_ORPHAN))])
        assert r.stdout == "  - Second\n    - Third\n"

    def test_survivor_after_dropped_deeper_keeps_indent(self, run_cli, write_md_file):
        # D (h2) follows dropped C (h4) and must keep its 2-space indent.
        r = run_cli(["--max-depth", "2", str(write_md_file("doc.md", DOC_DROP))])
        assert r.stdout == "- A\n  - B\n  - D\n"

    def test_order_preserved_after_filtering(self, run_cli, write_md_file):
        r = run_cli(["--max-depth", "2", str(write_md_file("doc.md", DOC_ALL + DOC_ALL))])
        assert r.stdout == ("- Alpha\n  - Beta\n") * 2


# ===========================================================================
# Phase 2 — attack tests (edge, adversarial, integration, deployment)
# ===========================================================================


class TestFenceIntegration:
    def test_fenced_headings_not_resurrected_by_any_n(self, run_cli, write_md_file):
        assert depths_of(DOC_FENCE) == [1, 2]  # premise: Fake1 is not extracted
        r = run_cli(["--max-depth", "100", str(write_md_file("doc.md", DOC_FENCE))])
        assert r.stdout == "- Real\n  - Real2\n"

    def test_unclosed_fence_swallows_rest_with_flag(self, run_cli, write_md_file):
        assert depths_of(DOC_UNCLOSED_FENCE) == [1]
        r = run_cli(["--max-depth", "6", str(write_md_file("doc.md", DOC_UNCLOSED_FENCE))])
        assert r.returncode == 0
        assert r.stdout == "- Real\n"

    def test_tilde_fence_with_flag(self, run_cli, write_md_file):
        assert depths_of(DOC_TILDE_FENCE) == [1]
        r = run_cli(["--max-depth", "1", str(write_md_file("doc.md", DOC_TILDE_FENCE))])
        assert r.stdout == "- Real\n"


class TestEncodingAndTextEdges:
    def test_bom_file_with_flag(self, run_cli, tmp_path):
        # If BOM handling broke, the first line would not parse as an h1
        # and N=1 output would be empty.
        bom = tmp_path / "bom.md"
        bom.write_bytes(BOM_DOC)
        r = run_cli(["--max-depth", "1", str(bom)])
        assert r.returncode == 0
        assert r.stdout == "- BOM Title\n"

    def test_crlf_input_with_flag(self, run_cli, tmp_path):
        crlf = tmp_path / "crlf.md"
        crlf.write_bytes(CRLF_DOC)
        r = run_cli(["--max-depth", "2", str(crlf)])
        assert r.stdout == "- One\n  - Two\n"  # no \r residue

    def test_unicode_heading_text_with_flag(self, run_cli, write_md_file):
        assert depths_of(DOC_UNICODE) == [1, 3]
        r = run_cli(["--max-depth", "1", str(write_md_file("doc.md", DOC_UNICODE))])
        assert r.stdout == "- 标题 一\n"
        r3 = run_cli(["--max-depth", "3", str(write_md_file("doc.md", DOC_UNICODE))])
        assert r3.stdout == "- 标题 一\n    - 🚀 Deep\n"

    def test_empty_text_heading_kept_and_dropped(self, run_cli, write_md_file):
        assert depths_of(DOC_EMPTY_TEXT) == [1, 2]
        r2 = run_cli(["--max-depth", "2", str(write_md_file("doc.md", DOC_EMPTY_TEXT))])
        assert r2.stdout == "- T\n  -\n"
        r1 = run_cli(["--max-depth", "1", str(write_md_file("doc.md", DOC_EMPTY_TEXT))])
        assert r1.stdout == "- T\n"

    def test_trailing_hashes_stripped_then_filtered(self, run_cli, write_md_file):
        assert mdoutline.extract_headings(DOC_TRAILING_HASHES.splitlines()) == [(2, "Title")]
        r = run_cli(["--max-depth", "2", str(write_md_file("doc.md", DOC_TRAILING_HASHES))])
        assert r.stdout == "  - Title\n"
        r1 = run_cli(["--max-depth", "1", str(write_md_file("doc.md", DOC_TRAILING_HASHES))])
        assert r1.stdout == ""


class TestHeadingRecognitionEdges:
    def test_leading_space_heading_counts_toward_depth(self, run_cli, write_md_file):
        # 3 leading spaces: still a heading. 4: not a heading at all.
        assert depths_of(DOC_LEADING_SPACES) == [1]
        r = run_cli(["--max-depth", "6", str(write_md_file("doc.md", DOC_LEADING_SPACES))])
        assert r.stdout == "- H1\n"

    def test_seven_hashes_never_a_heading_even_huge_n(self, run_cli, write_md_file):
        assert depths_of(DOC_SEVEN_HASHES) == [1]  # premise: 7# line ignored
        r = run_cli(["--max-depth", "50", str(write_md_file("doc.md", DOC_SEVEN_HASHES))])
        assert r.stdout == "- Real\n"


class TestEmptyAndErrorPaths:
    def test_n0_file_mode_empty_output_exit_0(self, run_cli, write_md_file):
        r = run_cli(["--max-depth", "0", str(write_md_file("doc.md", DOC_ALL))])
        assert r.returncode == 0
        assert r.stdout == ""

    def test_empty_input_with_flag(self, run_cli, write_md_file):
        r = run_cli(["--max-depth", "3", str(write_md_file("doc.md", ""))])
        assert r.returncode == 0
        assert r.stdout == ""

    def test_no_survivors_means_empty_output(self, run_cli, write_md_file):
        assert depths_of(DOC_ORPHAN) == [2, 3]  # no h1 anywhere
        r = run_cli(["--max-depth", "1", str(write_md_file("doc.md", DOC_ORPHAN))])
        assert r.returncode == 0
        assert r.stdout == ""

    def test_missing_file_with_flag_keeps_error_contract(self, run_cli):
        r = run_cli(["--max-depth", "2", "/nonexistent/mdoutline-probe.md"])
        assert r.returncode == 1
        assert r.stdout == ""
        assert "cannot read" in r.stderr

    def test_stdin_invalid_utf8_with_flag(self, run_cli):
        r = run_cli(["--max-depth", "1"], stdin=b"\xff\xfe# x\n")
        assert r.returncode == 1
        assert b"cannot read" in r.stderr

    def test_help_lists_max_depth(self, run_cli):
        r = run_cli(["--help"])
        assert r.returncode == 0
        assert "--max-depth" in r.stdout


class TestLibraryContract:
    HEADINGS = [(1, "a"), (2, "b"), (3, "c"), (6, "f")]

    def test_none_returns_all_as_new_list(self):
        out = mdoutline.filter_by_depth(self.HEADINGS, None)
        assert out == self.HEADINGS
        assert out is not self.HEADINGS

    def test_no_mutation_of_input(self):
        original = list(self.HEADINGS)
        mdoutline.filter_by_depth(self.HEADINGS, 2)
        mdoutline.filter_by_depth(self.HEADINGS, None)
        assert original == self.HEADINGS

    def test_boundaries(self):
        assert mdoutline.filter_by_depth([], 3) == []
        assert mdoutline.filter_by_depth(self.HEADINGS, 0) == []
        assert mdoutline.filter_by_depth(self.HEADINGS, 6) == self.HEADINGS
        assert mdoutline.filter_by_depth(self.HEADINGS, 2) == [(1, "a"), (2, "b")]

    def test_library_pipeline_equals_cli(self, run_cli, write_md_file):
        # extract -> filter -> render through the library must equal the CLI.
        headings = mdoutline.extract_headings(DOC_GAP.splitlines())
        outline = mdoutline.render_outline(mdoutline.filter_by_depth(headings, 2))
        r = run_cli(["--max-depth", "2", str(write_md_file("doc.md", DOC_GAP))])
        assert r.returncode == 0
        assert outline == r.stdout == "- Root\n"


class TestDeploymentReadiness:
    def test_console_script_entry_point_exists(self, run_cli):
        cmd = resolve_mdoutline_cmd()
        if cmd is None:
            pytest.skip("mdoutline command not found - set MDOUTLINE_BIN or install the package")
        r = run_cli(["--help"])
        assert r.returncode == 0
        assert "--max-depth" in r.stdout

    def test_python_m_matches_console_script(self, run_cli, write_md_file, monkeypatch):
        f = write_md_file("doc.md", DOC_ALL)
        script = run_cli(["--max-depth", "2", str(f)])
        monkeypatch.setenv("MDOUTLINE_BIN", f"{sys.executable} -m mdoutline")
        mod = run_cli(["--max-depth", "2", str(f)])
        assert mod.returncode == script.returncode == 0
        assert mod.stdout == script.stdout

    def test_broken_pipe_is_quiet_nonzero(self, tmp_path, run_cli_pipeline):
        # ~200KB outline piped into `head -n 1`: must exit 13 without a
        # traceback, exactly like the no-flag behavior (ticket-01 contract).
        big = tmp_path / "big.md"
        big.write_text("".join(f"# Title line {i}\n" for i in range(20000)))
        r = run_cli_pipeline(
            f"--max-depth 1 {shlex.quote(str(big))} | head -n 1 >/dev/null; exit ${{PIPESTATUS[0]}}",
            stdin="",
        )
        assert r.returncode == 13, (r.returncode, r.stderr)
        assert "Traceback" not in r.stderr

    def test_large_input_filter_smoke(self, run_cli, write_md_file):
        lines = []
        for i in range(1500):
            lines.append(f"# T{i}")
            lines.append(f"#### D{i}")
        r = run_cli(["--max-depth", "2", str(write_md_file("doc.md", "\n".join(lines) + "\n"))])
        assert r.returncode == 0
        expected = "".join(f"- T{i}\n" for i in range(1500))
        assert r.stdout == expected  # every h1 kept, every h4 dropped, byte-exact
