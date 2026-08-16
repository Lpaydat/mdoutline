"""Behavior verification for ticket-03: ``--numbers`` section numbering.

Integration verification of section numbering through the PUBLIC interfaces only:
  * the ``mdoutline`` console script (production entry point),
  * ``python -m mdoutline``,
  * the library API (``extract_headings`` / ``filter_by_depth`` / ``number_headings`` / ``render_outline``).

Numbering rules (implemented in ``number_headings``):
  * A heading at depth d increments counter[d] and resets ALL deeper counters to 0.
  * The number for a heading at depth d joins counter[1..d] with dots.
  * Format: depth 1 gets a trailing dot ("1.", "2."); depth >= 2 gets none ("1.1", "1.2.1").
  * Skipped intermediate levels render a mechanical 0: e.g., h1 followed directly by h3 -> "1.0.1".
  * Numbering is computed AFTER depth filtering; filtered-out headings consume NO numbers.

Rendering rules with ``--numbers``:
  * Non-empty text: "- 1. Intro" (indent + "- " + number + " " + text)
  * Empty-text heading: "- 1." (indent + "- " + number, NOTHING after it — no trailing space)
  * Indentation unchanged: 2 spaces per depth below h1

Without the flag, output must be byte-identical to the pre-change behavior.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # library probes work without editable install

import mdoutline  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures (documents). Premise assertions live in the tests that use them.
# ---------------------------------------------------------------------------

DOC_CANONICAL = "# A\n## B\n## C\n### D\n## E\n# F\n"
OUTLINE_CANONICAL_NUMBERS = "- 1. A\n  - 1.1 B\n  - 1.2 C\n    - 1.2.1 D\n  - 1.3 E\n- 2. F\n"
OUTLINE_CANONICAL_PLAIN = "- A\n  - B\n  - C\n    - D\n  - E\n- F\n"

DOC_EMPTY_TEXT = "# Title One\n##\n## Section Two\n"
OUTLINE_EMPTY_TEXT_NUMBERS = "- 1. Title One\n  - 1.1\n  - 1.2 Section Two\n"
OUTLINE_EMPTY_TEXT_PLAIN = "- Title One\n  -\n  - Section Two\n"

DOC_DEPTH_COMPOSE = "# H1\n## H2\n### H3\n## H2b\n# H1b\n"
OUTLINE_DEPTH_COMPOSE_NUMBERS = "- 1. H1\n  - 1.1 H2\n  - 1.2 H2b\n- 2. H1b\n"
OUTLINE_DEPTH_COMPOSE_PLAIN = "- H1\n  - H2\n    - H3\n  - H2b\n- H1b\n"

DOC_FENCE = "# Real\n```\n# Fake1\n## Fake2\n```\n## Real2\n"
OUTLINE_FENCE_NUMBERS = "- 1. Real\n  - 1.1 Real2\n"
OUTLINE_FENCE_PLAIN = "- Real\n  - Real2\n"

DOC_GAP = "# Root\n### Deep child\n"  # h1 then h3: skipped level renders 0
OUTLINE_GAP_NUMBERS = "- 1. Root\n    - 1.0.1 Deep child\n"
OUTLINE_GAP_PLAIN = "- Root\n    - Deep child\n"

DOC_UNICODE = "# 标题 一\n### 🚀 Deep\n"
OUTLINE_UNICODE_NUMBERS = "- 1. 标题 一\n    - 1.0.1 🚀 Deep\n"
OUTLINE_UNICODE_PLAIN = "- 标题 一\n    - 🚀 Deep\n"


def _cli() -> list[str]:
    # MDOUTLINE_BIN lets verification harnesses target a specific binary
    # (e.g. a mutated clone); production behavior is unchanged.
    override = os.environ.get("MDOUTLINE_BIN")
    if override:
        return override.split()
    exe = shutil.which("mdoutline")
    return [exe] if exe else [sys.executable, "-m", "mdoutline"]


def run_cli(*args: str, stdin: str | bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    if isinstance(stdin, str):
        stdin = stdin.encode()
    return subprocess.run(
        _cli() + list(args),
        input=stdin,
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=120,
    )


@pytest.fixture()
def doc_file(tmp_path: Path):
    def _write(content: str | bytes, name: str = "doc.md") -> Path:
        p = tmp_path / name
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
        return p

    return _write


# ===========================================================================
# Phase 1 — core numbering behavior
# ===========================================================================


class TestCanonicalVector:
    def test_numbers_on_file_exact_output(self, doc_file):
        """Canonical vector h1,h2,h2,h3,h2,h1 -> exact numbered lines."""
        r = run_cli("--numbers", str(doc_file(DOC_CANONICAL)))
        assert r.returncode == 0, r.stderr
        assert r.stdout == OUTLINE_CANONICAL_NUMBERS.encode()

    def test_counter_reset_after_nested(self, doc_file):
        """After 1.2.1 the next h2 renders 1.3; the next h1 renders 2."""
        r = run_cli("--numbers", str(doc_file(DOC_CANONICAL)))
        lines = r.stdout.decode().splitlines()
        # Verify exact sequence
        assert lines[0] == "- 1. A"
        assert lines[1] == "  - 1.1 B"
        assert lines[2] == "  - 1.2 C"
        assert lines[3] == "    - 1.2.1 D"
        assert lines[4] == "  - 1.3 E"  # h2 after h3, not 1.4 or 2.1
        assert lines[5] == "- 2. F"  # h1 resets to 2


class TestEmptyTextHeadings:
    def test_empty_text_renders_without_trailing_space(self, doc_file):
        """Empty-text heading renders as '- 1.' with no trailing space."""
        r = run_cli("--numbers", str(doc_file(DOC_EMPTY_TEXT)))
        assert r.returncode == 0
        lines = r.stdout.decode().splitlines()
        assert lines[1] == "  - 1.1"  # No trailing space after the number
        # Verify no trailing whitespace on any line
        for line in lines:
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    def test_empty_text_correct_indent(self, doc_file):
        """Empty-text heading has correct indentation for its depth."""
        r = run_cli("--numbers", str(doc_file(DOC_EMPTY_TEXT)))
        assert r.returncode == 0
        lines = r.stdout.decode().splitlines()
        # h2 has 2 spaces indent
        assert lines[1].startswith("  - ")
        assert lines[2].startswith("  - ")


class TestDepthComposition:
    def test_numbers_with_max_depth_filtered_out_no_number(self, doc_file):
        """--numbers + --max-depth 2: filtered h3 gets no number."""
        r = run_cli("--numbers", "--max-depth", "2", str(doc_file(DOC_DEPTH_COMPOSE)))
        assert r.returncode == 0
        assert r.stdout == OUTLINE_DEPTH_COMPOSE_NUMBERS.encode()
        # The filtered-out h3 doesn't consume a number: h2b is 1.2, not 1.3
        lines = r.stdout.decode().splitlines()
        assert lines[0] == "- 1. H1"
        assert lines[1] == "  - 1.1 H2"
        assert lines[2] == "  - 1.2 H2b"  # h2b is 1.2, not 1.3
        assert lines[3] == "- 2. H1b"

    def test_max_depth_only_affects_numbering_inputs(self, doc_file):
        """Depth filtering happens before numbering; survivors keep their numbers."""
        # Same document with and without max-depth should produce different outputs
        r_full = run_cli("--numbers", str(doc_file(DOC_DEPTH_COMPOSE)))
        r_depth = run_cli("--numbers", "--max-depth", "2", str(doc_file(DOC_DEPTH_COMPOSE)))
        assert r_full.returncode == r_depth.returncode == 0
        assert r_full.stdout != r_depth.stdout
        # Full output has the h3
        assert b"1.1.1" in r_full.stdout
        # Depth-limited output does not
        assert b"1.1.1" not in r_depth.stdout


class TestFlagAbsentRegression:
    def test_flag_absent_byte_identical_plain_outline(self, doc_file):
        """Without --numbers, output is byte-identical to pre-change behavior."""
        f = doc_file(DOC_CANONICAL)
        r_plain = run_cli(str(f))
        assert r_plain.returncode == 0
        assert r_plain.stdout == OUTLINE_CANONICAL_PLAIN.encode()

    def test_flag_absent_vs_flag_present_same_doc(self, doc_file):
        """Compare no-flag vs with-flag on the same file to ensure no regression."""
        f = doc_file(DOC_CANONICAL)
        r_plain = run_cli(str(f))
        r_numbers = run_cli("--numbers", str(f))
        assert r_plain.returncode == r_numbers.returncode == 0
        # Plain output should not have numbers
        assert b"1." not in r_plain.stdout or b"- 1." not in r_plain.stdout
        # Numbers output should have numbers
        assert b"- 1." in r_numbers.stdout
        # Plain output should match expected plain outline exactly
        assert r_plain.stdout == OUTLINE_CANONICAL_PLAIN.encode()

    def test_flag_absent_multiple_docs(self, doc_file):
        """Regression check across multiple document types."""
        docs = [
            (DOC_EMPTY_TEXT, OUTLINE_EMPTY_TEXT_PLAIN),
            (DOC_DEPTH_COMPOSE, OUTLINE_DEPTH_COMPOSE_PLAIN),
            (DOC_FENCE, OUTLINE_FENCE_PLAIN),
            (DOC_GAP, OUTLINE_GAP_PLAIN),
            (DOC_UNICODE, OUTLINE_UNICODE_PLAIN),
        ]
        for doc, expected in docs:
            r = run_cli(str(doc_file(doc)))
            assert r.returncode == 0, f"Failed for doc: {doc[:50]}"
            assert r.stdout == expected.encode(), f"Output mismatch for doc: {doc[:50]}"


class TestStdinPath:
    def test_stdin_numbers_equals_file_numbers(self, doc_file):
        """--numbers reading from stdin yields same output as file path."""
        f = doc_file(DOC_CANONICAL)
        r_file = run_cli("--numbers", str(f))
        r_stdin = run_cli("--numbers", stdin=DOC_CANONICAL)
        assert r_file.returncode == r_stdin.returncode == 0
        assert r_file.stdout == r_stdin.stdout

    def test_stdin_empty_text_numbers(self, doc_file):
        """Stdin mode with empty-text headings."""
        r_stdin = run_cli("--numbers", stdin=DOC_EMPTY_TEXT)
        assert r_stdin.returncode == 0
        assert r_stdin.stdout == OUTLINE_EMPTY_TEXT_NUMBERS.encode()

    def test_stdin_depth_composition_numbers(self, doc_file):
        """Stdin mode with --numbers + --max-depth composition."""
        r_stdin = run_cli("--numbers", "--max-depth", "2", stdin=DOC_DEPTH_COMPOSE)
        assert r_stdin.returncode == 0
        assert r_stdin.stdout == OUTLINE_DEPTH_COMPOSE_NUMBERS.encode()


class TestFencedCodeBlocks:
    def test_fenced_headings_still_skipped_with_numbers(self, doc_file):
        """Headings inside ``` fences are still skipped when --numbers is on."""
        r = run_cli("--numbers", str(doc_file(DOC_FENCE)))
        assert r.returncode == 0
        assert r.stdout == OUTLINE_FENCE_NUMBERS.encode()
        # Fake1 and Fake2 should not appear or affect numbering
        lines = r.stdout.decode().splitlines()
        assert len(lines) == 2  # Only Real and Real2
        assert lines[0] == "- 1. Real"
        assert lines[1] == "  - 1.1 Real2"  # Real2 is 1.1, not 1.2 (Fake1/2 skipped)

    def test_unclosed_fence_with_numbers(self, doc_file):
        """Unclosed fence swallows rest even with --numbers."""
        doc = "# Real\n```\n# Fake\n## AlsoFake\n"
        r = run_cli("--numbers", stdin=doc)
        assert r.returncode == 0
        lines = r.stdout.decode().splitlines()
        assert len(lines) == 1
        assert lines[0] == "- 1. Real"  # Only the h1 before the fence

    def test_tilde_fence_with_numbers(self, doc_file):
        """Tilde fences also skip headings with --numbers."""
        doc = "~~~\n# Fake\n~~~\n# Real\n"
        r = run_cli("--numbers", stdin=doc)
        assert r.returncode == 0
        assert r.stdout == b"- 1. Real\n"  # Fake skipped


class TestSkippedLevels:
    def test_skipped_level_renders_mechanical_zero(self, doc_file):
        """Skipped intermediate level renders a mechanical 0: h1 then h3 -> 1.0.1."""
        r = run_cli("--numbers", str(doc_file(DOC_GAP)))
        assert r.returncode == 0
        assert r.stdout == OUTLINE_GAP_NUMBERS.encode()
        lines = r.stdout.decode().splitlines()
        assert lines[1] == "    - 1.0.1 Deep child"  # h3 after h1, no h2

    def test_multiple_skipped_levels(self, doc_file):
        """Multiple skipped levels: h1 then h4 -> 1.0.0.1."""
        doc = "# A\n#### B\n"
        r = run_cli("--numbers", stdin=doc)
        assert r.returncode == 0
        lines = r.stdout.decode().splitlines()
        assert lines[1] == "      - 1.0.0.1 B"


class TestUnicodeAndEncoding:
    def test_unicode_text_with_numbers(self, doc_file):
        """Unicode heading text works with --numbers."""
        r = run_cli("--numbers", str(doc_file(DOC_UNICODE)))
        assert r.returncode == 0
        assert r.stdout == OUTLINE_UNICODE_NUMBERS.encode()
        lines = r.stdout.decode().splitlines()
        assert lines[0] == "- 1. 标题 一"
        assert lines[1] == "    - 1.0.1 🚀 Deep"


class TestHelpAndFlagParsing:
    def test_help_exits_zero_and_mentions_flag(self):
        """--help exits 0 and mentions the --numbers flag."""
        r = run_cli("--help")
        assert r.returncode == 0
        assert b"--numbers" in r.stdout
        assert b"section numbers" in r.stdout

    def test_flag_store_true_no_value_accepted(self, doc_file):
        """--numbers is a store_true flag and rejects an explicit value."""
        f = doc_file(DOC_CANONICAL)
        r = run_cli("--numbers=true", str(f))
        assert r.returncode == 2  # argparse error
        assert b"ignored explicit argument" in r.stderr


# ===========================================================================
# Phase 2 — library contract verification
# ===========================================================================


class TestLibraryNumberingPipeline:
    def test_number_headings_library_contract(self):
        """Verify number_headings returns (depth, text, number) tuples."""
        headings = [(1, "A"), (2, "B"), (2, "C"), (3, "D"), (2, "E"), (1, "F")]
        numbered = mdoutline.number_headings(headings)
        assert numbered == [
            (1, "A", "1."),
            (2, "B", "1.1"),
            (2, "C", "1.2"),
            (3, "D", "1.2.1"),
            (2, "E", "1.3"),
            (1, "F", "2."),
        ]

    def test_render_outline_accepts_numbered_tuples(self):
        """render_outline accepts (depth, text, number) tuples and renders correctly."""
        numbered = [(1, "A", "1."), (2, "B", "1.1"), (2, "C", "1.2")]
        outline = mdoutline.render_outline(numbered)
        assert outline == "- 1. A\n  - 1.1 B\n  - 1.2 C\n"

    def test_render_outline_mixed_formats(self):
        """render_outline handles both (depth, text) and (depth, text, number) tuples."""
        # Plain tuples
        plain = [(1, "A"), (2, "B")]
        assert mdoutline.render_outline(plain) == "- A\n  - B\n"
        # Numbered tuples
        numbered = [(1, "A", "1."), (2, "B", "1.1")]
        assert mdoutline.render_outline(numbered) == "- 1. A\n  - 1.1 B\n"

    def test_library_pipeline_matches_cli_numbers(self, doc_file):
        """Library pipeline (extract -> filter -> number -> render) matches CLI with --numbers."""
        doc = DOC_CANONICAL
        # CLI
        r_cli = run_cli("--numbers", str(doc_file(doc)))
        assert r_cli.returncode == 0

        # Library
        headings = mdoutline.extract_headings(doc.splitlines())
        filtered = mdoutline.filter_by_depth(headings, None)
        numbered = mdoutline.number_headings(filtered)
        outline = mdoutline.render_outline(numbered)

        assert outline.encode() == r_cli.stdout


class TestEmptyInputs:
    def test_empty_input_with_numbers(self, doc_file):
        """Empty input with --numbers produces empty output."""
        r = run_cli("--numbers", str(doc_file("")))
        assert r.returncode == 0
        assert r.stdout == b""

    def test_no_headings_with_numbers(self, doc_file):
        """Document with no headings and --numbers produces empty output."""
        doc = "Just some text\nno headings here\n"
        r = run_cli("--numbers", str(doc_file(doc)))
        assert r.returncode == 0
        assert r.stdout == b""


class TestEdgeCases:
    def test_single_heading_numbers(self, doc_file):
        """Single heading with --numbers."""
        doc = "# Only One\n"
        r = run_cli("--numbers", str(doc_file(doc)))
        assert r.returncode == 0
        assert r.stdout == b"- 1. Only One\n"

    def test_all_same_depth_numbers(self, doc_file):
        """All headings at same depth with --numbers."""
        doc = "# A\n# B\n# C\n"
        r = run_cli("--numbers", str(doc_file(doc)))
        assert r.returncode == 0
        assert r.stdout == b"- 1. A\n- 2. B\n- 3. C\n"

    def test_deep_nesting_numbers(self, doc_file):
        """Deep nesting (h1->h2->h3->h4->h5->h6) with --numbers."""
        doc = "# L1\n## L2\n### L3\n#### L4\n##### L5\n###### L6\n"
        r = run_cli("--numbers", str(doc_file(doc)))
        assert r.returncode == 0
        lines = r.stdout.decode().splitlines()
        assert lines[0] == "- 1. L1"
        assert lines[1] == "  - 1.1 L2"
        assert lines[2] == "    - 1.1.1 L3"
        assert lines[3] == "      - 1.1.1.1 L4"
        assert lines[4] == "        - 1.1.1.1.1 L5"
        assert lines[5] == "          - 1.1.1.1.1.1 L6"


class TestDeploymentReadiness:
    def test_console_script_numbers_flag_works(self):
        """Production console script 'mdoutline' supports --numbers."""
        exe = shutil.which("mdoutline")
        assert exe, "production console script 'mdoutline' not on PATH"
        r = subprocess.run(
            [exe, "--help"],
            capture_output=True,
            timeout=60,
        )
        assert r.returncode == 0
        assert b"--numbers" in r.stdout

    def test_console_script_numbers_output(self, doc_file):
        """Console script with --numbers produces correct output."""
        exe = shutil.which("mdoutline")
        if not exe:
            pytest.skip("production console script 'mdoutline' not on PATH")
        f = doc_file(DOC_CANONICAL)
        r = subprocess.run(
            [exe, "--numbers", str(f)],
            capture_output=True,
            timeout=60,
        )
        assert r.returncode == 0
        assert r.stdout == OUTLINE_CANONICAL_NUMBERS.encode()

    def test_python_m_matches_console_script_numbers(self, doc_file):
        """python -m mdoutline --numbers matches console script output."""
        exe = shutil.which("mdoutline")
        if not exe:
            pytest.skip("production console script 'mdoutline' not on PATH")
        f = doc_file(DOC_CANONICAL)
        script = subprocess.run(
            [exe, "--numbers", str(f)],
            capture_output=True,
            timeout=60,
        )
        mod = subprocess.run(
            [sys.executable, "-m", "mdoutline", "--numbers", str(f)],
            capture_output=True,
            cwd=REPO_ROOT,
            timeout=60,
        )
        assert mod.returncode == script.returncode == 0
        assert mod.stdout == script.stdout
