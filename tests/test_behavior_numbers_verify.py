"""INDEPENDENT adversarial behavior verification for ticket-03 ``--numbers``.

Written by the verifier (card t_2a2deaf8) against the PUBLIC interfaces only:
the ``python -m mdoutline`` module CLI, the installed ``mdoutline`` console
script (production entry point), and the library API.

Every expected output below was derived BY HAND from the normative numbering
RULE in spec card t_674c56b1, not copied from any existing test:

  R1  A heading at depth d increments counter[d] and resets ALL deeper counters.
  R2  The number for a heading at depth d joins counter[1..d] with dots.
  R3  Format: depth 1 renders a trailing dot ("1.", "2."); depth >= 2 does not.
  R4  Skipped intermediate levels render a mechanical 0 (h1 then h3 -> "1.0.1").
  R5  Numbering is computed over headings that SURVIVE --max-depth filtering.
  R6  Flag absent = plain bullets, byte-identical to ticket-1 output.

Note on the spec's AC2 parenthetical: it says "after ``1.1``, ``1.2`` a deeper
h3 restarts at ``1.2.1``; next h2 is ``2.``" -- under the rule the next h2
after ``1.2.1`` is ``1.3``; only the next H1 is ``2.``. The ticket itself
flags that one plan example drifted from its own rule, so the RULE wins.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conftest import resolve_mdoutline_cmd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # noqa: E402  (library probes, no install needed)

import mdoutline  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def run_cli_module(run_cli, monkeypatch):
    """Run `python -m mdoutline` through the shared seam by pointing
    MDOUTLINE_BIN at the module invocation (same pattern as the -m parity
    tests in test_behavior_numbers.py / test_behavior_depth.py)."""
    monkeypatch.setenv("MDOUTLINE_BIN", f"{sys.executable} -m mdoutline")
    return run_cli


# ===========================================================================
# Phase 1 — spec AC matrix, expectations hand-derived from the rule
# ===========================================================================


class TestSpecAcMatrix:
    """One behavior test per acceptance criterion in spec card t_674c56b1."""

    def test_ac1_numbers_between_bullet_and_text(self, run_cli_module, write_md_file):
        """AC1: numbers sit between bullet and text: ``- 1. Intro``, ``- 1.1 Setup``."""
        p = write_md_file("doc.md", "# Intro\n## Setup\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.returncode == 0, cp.stderr
        assert cp.stdout == "- 1. Intro\n  - 1.1 Setup\n"

    def test_ac1_exact_canonical_vector(self, run_cli_module, write_md_file):
        """AC1/R1-R3 over the canonical 6-heading vector, full byte-exact output."""
        p = write_md_file("doc.md", "# A\n## B\n## C\n### D\n## E\n# F\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == ("- 1. A\n  - 1.1 B\n  - 1.2 C\n    - 1.2.1 D\n  - 1.3 E\n- 2. F\n")

    def test_ac2_counter_reset_rule_not_drifted_example(self, run_cli_module, write_md_file):
        """AC2 (normative rule): after 1.1, 1.2 and a deeper h3 at 1.2.1, the
        NEXT H2 is 1.3 (deeper reset, sibling counter continues) and the next
        H1 is 2. The AC's 'next h2 is 2.' parenthetical contradicts R1/R2."""
        p = write_md_file("doc.md", "# T\n## S1\n## S2\n### Deep\n## S3\n# U\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == (
            "- 1. T\n  - 1.1 S1\n  - 1.2 S2\n    - 1.2.1 Deep\n  - 1.3 S3\n- 2. U\n"
        )

    def test_ac2_deeper_counters_reset_between_siblings(self, run_cli_module, write_md_file):
        """R1: two h3s under different h2s both restart at .1 (deeper reset)."""
        p = write_md_file("doc.md", "# R\n## A\n### x\n### y\n## B\n### z\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == (
            "- 1. R\n  - 1.1 A\n    - 1.1.1 x\n    - 1.1.2 y\n  - 1.2 B\n    - 1.2.1 z\n"
        )

    def test_ac3_numbers_only_surviving_headings(self, run_cli_module, write_md_file):
        """AC3/R5: ``--numbers --max-depth 2`` numbers only survivors; dropped
        h3/h4 consume no output lines at all."""
        p = write_md_file("doc.md", "# A\n## B\n### C\n#### D\n## E\n")
        cp = run_cli_module(["--numbers", "--max-depth", "2", str(p)])
        assert cp.returncode == 0, cp.stderr
        assert cp.stdout == "- 1. A\n  - 1.1 B\n  - 1.2 E\n"

    def test_ac3_survivor_numbers_are_rule_correct_post_filter(self, run_cli_module, write_md_file):
        """R5: with max-depth 2, an h3 between two h2s is removed AND leaves no
        mechanical-zero trace; the following h2 is 1.1 (first h2 survivor)."""
        p = write_md_file("doc.md", "# A\n### C\n## B\n")
        cp = run_cli_module(["--numbers", "--max-depth", "2", str(p)])
        assert cp.stdout == "- 1. A\n  - 1.1 B\n"

    def test_ac3_depth_values_survive_filtering_for_indent(self, run_cli_module, write_md_file):
        """R5: survivors keep their ORIGINAL depth for indentation (filter does
        not re-level): h3 survivor under max-depth 3 still indents 4 spaces."""
        p = write_md_file("doc.md", "# A\n## B\n### C\n## D\n")
        cp = run_cli_module(["--numbers", "--max-depth", "3", str(p)])
        assert cp.stdout == ("- 1. A\n  - 1.1 B\n    - 1.1.1 C\n  - 1.2 D\n")

    def test_ac4_flag_absent_plain_bullets_unchanged(self, run_cli_module, write_md_file):
        """AC4/R6: no flag = ticket-1 plain output, byte-exact."""
        p = write_md_file("doc.md", "# A\n## B\n## C\n### D\n## E\n# F\n")
        cp = run_cli_module([str(p)])
        assert cp.stdout == "- A\n  - B\n  - C\n    - D\n  - E\n- F\n"

    def test_ac4_flag_absent_not_secretly_numbered(self, run_cli_module):
        """R6: plain output contains no digit-dot patterns from numbering."""
        cp = run_cli_module([], stdin="# Solo\n")
        assert cp.returncode == 0
        assert cp.stdout == "- Solo\n"

    def test_ac5_unit_reset_semantics_via_library(self):
        """AC5 (library half): counter reset semantics directly through the
        public function, expectations from R1/R2/R3."""
        got = mdoutline.number_headings(
            [(1, "A"), (2, "B"), (2, "C"), (3, "D"), (2, "E"), (1, "F")]
        )
        assert got == [
            (1, "A", "1."),
            (2, "B", "1.1"),
            (2, "C", "1.2"),
            (3, "D", "1.2.1"),
            (2, "E", "1.3"),
            (1, "F", "2."),
        ]

    def test_ac5_subprocess_numbers_alone_and_combined(self, run_cli_module, write_md_file):
        """AC5 (subprocess half): both --numbers alone and composed with
        --max-depth verified through a spawned CLI process (whole class does)."""
        p = write_md_file("doc.md", "# A\n## B\n### C\n")
        alone = run_cli_module(["--numbers", str(p)])
        combined = run_cli_module(["--numbers", "--max-depth", "2", str(p)])
        assert alone.stdout == "- 1. A\n  - 1.1 B\n    - 1.1.1 C\n"
        assert combined.stdout == "- 1. A\n  - 1.1 B\n"


# ===========================================================================
# Phase 2 — attack tests (gaps in any Phase-1-only suite)
# ===========================================================================


class TestAttackRuleEdges:
    """Adversarial inputs derived from the RULE itself."""

    def test_doc_starts_at_h2_mechanical_zero_in_front(self, run_cli_module, write_md_file):
        """R2/R4 hostile shape: no h1 at all -- the first h2 renders 0.1
        (counter[1] never incremented), and a later h1 starts 1."""
        p = write_md_file("doc.md", "## First\n## Second\n# Later\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "  - 0.1 First\n  - 0.2 Second\n- 1. Later\n"

    def test_doc_starting_at_h6_full_zero_prefix(self, run_cli_module, write_md_file):
        """Worst legal depth with no ancestors: h6 alone -> 0.0.0.0.0.1,
        indented 2*(6-1) = 10 spaces."""
        p = write_md_file("doc.md", "###### Deep\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "          - 0.0.0.0.0.1 Deep\n"

    def test_full_six_level_chain(self, run_cli_module, write_md_file):
        """All six depths nested, indent +2 spaces per level below h1:
        1. / 1.1 / 1.1.1 / 1.1.1.1 / 1.1.1.1.1 / 1.1.1.1.1.1."""
        p = write_md_file("doc.md", "# a\n## b\n### c\n#### d\n##### e\n###### f\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == (
            "- 1. a\n"
            "  - 1.1 b\n"
            "    - 1.1.1 c\n"
            "      - 1.1.1.1 d\n"
            "        - 1.1.1.1.1 e\n"
            "          - 1.1.1.1.1.1 f\n"
        )

    def test_two_digit_counter_join_unambiguous(self, run_cli_module, write_md_file):
        """12 h2 siblings: the 12th is 1.12 (join, not zero-pad)."""
        doc = "# T\n" + "".join(f"## H{i}\n" for i in range(1, 13))
        p = write_md_file("doc.md", doc)
        cp = run_cli_module(["--numbers", str(p)])
        lines = cp.stdout.splitlines()
        assert lines[0] == "- 1. T"
        assert lines[11] == "  - 1.11 H11"
        assert lines[12] == "  - 1.12 H12"

    def test_heading_text_that_looks_like_a_number(self, run_cli_module, write_md_file):
        """Hostile text: heading whose text is itself '2. Fake' must not
        perturb counters -- numbering and text stay separated."""
        p = write_md_file("doc.md", "# 1. Real\n## 3. Fake\n# 9. Also real\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1. 1. Real\n  - 1.1 3. Fake\n- 2. 9. Also real\n"

    def test_empty_text_heading_no_trailing_space(self, run_cli_module, write_md_file):
        """Empty-text survivor renders '- 1.1' with NO trailing space."""
        p = write_md_file("doc.md", "# T\n##\n## S\n")
        cp = run_cli_module(["--numbers", str(p)])
        lines = cp.stdout.splitlines()
        assert lines[1] == "  - 1.1"
        assert "  - 1.1 " not in cp.stdout

    def test_empty_text_h1_number_only_line(self, run_cli_module, write_md_file):
        p = write_md_file("doc.md", "#\n## X\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1.\n  - 1.1 X\n"

    def test_skipped_level_mechanical_zero_then_rejoin(self, run_cli_module, write_md_file):
        """R4: h1 -> h3 gives 1.0.1; a following h2 gives 1.1 (not 1.2)."""
        p = write_md_file("doc.md", "# R\n### x\n## y\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1. R\n    - 1.0.1 x\n  - 1.1 y\n"

    def test_unicode_and_emoji_text(self, run_cli_module, write_md_file):
        p = write_md_file("doc.md", "# 标题 一\n### 🚀 深\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1. 标题 一\n    - 1.0.1 🚀 深\n"

    def test_crlf_input(self, run_cli_module, write_md_file):
        p = write_md_file("doc.md", "# A\r\n## B\r\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1. A\n  - 1.1 B\n"

    def test_bom_via_stdin_bytes(self, run_cli_module):
        cp = run_cli_module(["--numbers"], stdin="\ufeff# A\n## B\n")
        assert cp.returncode == 0
        assert cp.stdout == "- 1. A\n  - 1.1 B\n"

    def test_indented_heading_three_spaces(self, run_cli_module, write_md_file):
        """3 leading spaces is still a heading (CommonMark), same depth."""
        p = write_md_file("doc.md", "   # A\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1. A\n"

    def test_trailing_closing_hashes_do_not_eat_the_number(self, run_cli_module, write_md_file):
        p = write_md_file("doc.md", "# R\n## T ##\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1. R\n  - 1.1 T\n"

    def test_fenced_fake_headings_never_numbered(self, run_cli_module, write_md_file):
        p = write_md_file("doc.md", "# Real\n```\n# Fake1\n## Fake2\n```\n## Real2\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1. Real\n  - 1.1 Real2\n"

    def test_tilde_fence_and_unclosed_fence(self, run_cli_module, write_md_file):
        p = write_md_file("doc.md", "# Real\n~~~\n# Fake\n~~~\n## Real2\n```\n# Trapped\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.stdout == "- 1. Real\n  - 1.1 Real2\n"

    def test_max_depth_0_kills_everything(self, run_cli_module, write_md_file):
        """Boundary N=0 (ticket-02 contract): nothing survives, empty stdout, rc 0."""
        p = write_md_file("doc.md", "# A\n## B\n")
        cp = run_cli_module(["--numbers", "--max-depth", "0", str(p)])
        assert cp.returncode == 0
        assert cp.stdout == ""

    def test_max_depth_above_six_keeps_all(self, run_cli_module, write_md_file):
        """N=7 filters nothing; h6 directly under h1 still renders mechanical
        zeros (1.0.0.0.0.1) per R4, indent 10 spaces."""
        p = write_md_file("doc.md", "# A\n###### Z\n")
        cp = run_cli_module(["--numbers", "--max-depth", "7", str(p)])
        assert cp.stdout == "- 1. A\n          - 1.0.0.0.0.1 Z\n"

    def test_flag_order_independent(self, run_cli_module, write_md_file):
        p = write_md_file("doc.md", "# A\n### C\n## B\n")
        a = run_cli_module(["--numbers", "--max-depth", "2", str(p)])
        b = run_cli_module(["--max-depth", "2", "--numbers", str(p)])
        assert a.stdout == b.stdout == "- 1. A\n  - 1.1 B\n"

    def test_stdin_equals_file_for_numbers(self, run_cli_module, write_md_file):
        doc = "# A\n## B\n### C\n"
        p = write_md_file("doc.md", doc)
        via_file = run_cli_module(["--numbers", str(p)])
        via_stdin = run_cli_module(["--numbers"], stdin=doc)
        assert via_file.stdout == via_stdin.stdout


class TestAttackCliRobustness:
    """Error paths and hostile invocations with --numbers present."""

    def test_numbers_with_value_rejected(self, run_cli_module):
        cp = run_cli_module(["--numbers=5"], stdin="# A\n")
        assert cp.returncode == 2
        assert "usage" in cp.stderr.lower()

    def test_missing_file_clean_error_rc1(self, run_cli_module):
        cp = run_cli_module(["--numbers", "/nonexistent/zz.md"])
        assert cp.returncode == 1
        assert cp.stdout == ""
        assert "cannot read" in cp.stderr
        assert "Traceback" not in cp.stderr

    def test_invalid_utf8_file_clean_error_rc1(self, run_cli_module, tmp_path):
        p = tmp_path / "bad.md"
        p.write_bytes(b"# A\n## \xff\xfe broken\n")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.returncode == 1
        assert "Traceback" not in cp.stderr
        assert "cannot read" in cp.stderr

    def test_empty_stdin_rc0_empty_stdout(self, run_cli_module):
        cp = run_cli_module(["--numbers"], stdin="")
        assert cp.returncode == 0
        assert cp.stdout == ""

    def test_no_headings_doc_rc0_empty_stdout(self, run_cli_module):
        cp = run_cli_module(["--numbers"], stdin="plain text\n\nno headings\n")
        assert cp.returncode == 0
        assert cp.stdout == ""

    def test_help_mentions_numbers_rc0(self, run_cli_module):
        cp = run_cli_module(["--help"])
        assert cp.returncode == 0
        assert "--numbers" in cp.stdout


class TestAttackProductionEntry:
    """Deployment readiness: the installed console script is the production
    path; it must behave identically to ``python -m mdoutline``."""

    def test_console_script_canonical_numbers(self, run_cli, write_md_file):
        cmd = resolve_mdoutline_cmd()
        if cmd is None:
            pytest.skip("mdoutline command not found - set MDOUTLINE_BIN or install the package")
        p = write_md_file("doc.md", "# A\n## B\n## C\n### D\n## E\n# F\n")
        cp = run_cli(["--numbers", str(p)])
        assert cp.returncode == 0, cp.stderr
        assert cp.stdout == ("- 1. A\n  - 1.1 B\n  - 1.2 C\n    - 1.2.1 D\n  - 1.3 E\n- 2. F\n")

    def test_console_script_combined_flags_stdin(self, run_cli):
        cmd = resolve_mdoutline_cmd()
        if cmd is None:
            pytest.skip("mdoutline command not found - set MDOUTLINE_BIN or install the package")
        doc = "# A\n## B\n### C\n#### D\n"
        cp = run_cli(["--numbers", "--max-depth", "2"], stdin=doc)
        assert cp.returncode == 0
        assert cp.stdout == "- 1. A\n  - 1.1 B\n"

    def test_console_script_equals_module_cli(self, run_cli, write_md_file, monkeypatch):
        """Byte-parity between production entry point and module invocation."""
        cmd = resolve_mdoutline_cmd()
        if cmd is None:
            pytest.skip("mdoutline command not found - set MDOUTLINE_BIN or install the package")
        doc = "# T\n## S1\n## S2\n### Deep\n## S3\n# U\n"
        p = write_md_file("doc.md", doc)
        cs = run_cli(["--numbers", str(p)])
        monkeypatch.setenv("MDOUTLINE_BIN", f"{sys.executable} -m mdoutline")
        mm = run_cli(["--numbers", str(p)])
        assert cs.returncode == mm.returncode == 0
        assert cs.stdout == mm.stdout
        assert cs.stderr == mm.stderr

    def test_big_document_5000_headings(self, run_cli_module, tmp_path):
        """Hostile scale: 5001 headings; exact first/last lines, single run."""
        doc = "# T\n" + "".join(f"## H{i}\n" for i in range(1, 5001))
        p = tmp_path / "big.md"
        p.write_text(doc, encoding="utf-8")
        cp = run_cli_module(["--numbers", str(p)])
        assert cp.returncode == 0, cp.stderr
        lines = cp.stdout.splitlines()
        assert len(lines) == 5001
        assert lines[1] == "  - 1.1 H1"
        assert lines[-1] == "  - 1.5000 H5000"

    def test_library_pipeline_matches_cli_byte_for_byte(self, run_cli_module, write_md_file):
        """The public library composition must equal the CLI product."""
        doc = "# H1\n## H2\n### H3\n## H2b\n# H1b\n"
        p = write_md_file("doc.md", doc)
        cp = run_cli_module(["--numbers", "--max-depth", "2", str(p)])
        headings = mdoutline.extract_headings(doc.splitlines())
        headings = mdoutline.filter_by_depth(headings, 2)
        numbered = mdoutline.number_headings(headings)
        assert mdoutline.render_outline(numbered) == cp.stdout


class TestAttackLibraryContract:
    """Independent library-level probes (public API only)."""

    def test_empty_input_returns_empty_list(self):
        assert mdoutline.number_headings([]) == []

    def test_input_list_not_mutated(self):
        src = [(1, "A"), (2, "B"), (3, "C")]
        snapshot = list(src)
        mdoutline.number_headings(src)
        assert src == snapshot

    def test_out_of_order_depth_jumps(self):
        """h1 then h4 -> 1.0.0.1 (two mechanical zeros); then h2 -> 1.1."""
        got = mdoutline.number_headings([(1, "A"), (4, "B"), (2, "C")])
        assert [n for _, _, n in got] == ["1.", "1.0.0.1", "1.1"]

    def test_all_h1_sequence(self):
        got = mdoutline.number_headings([(1, "A"), (1, "B"), (1, "C")])
        assert [n for _, _, n in got] == ["1.", "2.", "3."]

    def test_trailing_dot_only_at_depth_one(self):
        got = mdoutline.number_headings([(1, "A"), (2, "B")])
        assert got[0][2].endswith(".") and got[0][2] == "1."
        assert not got[1][2].endswith(".")

    def test_render_outline_numbered_empty_text(self):
        out = mdoutline.render_outline([(2, "", "1.1")])
        assert out == "  - 1.1\n"

    def test_render_outline_plain_two_tuples_unchanged(self):
        out = mdoutline.render_outline([(1, "A"), (2, "B")])
        assert out == "- A\n  - B\n"
