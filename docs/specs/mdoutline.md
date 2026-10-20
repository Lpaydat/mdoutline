# mdoutline — Markdown outline extractor

Repo: this repository

I want a small CLI that shows the heading structure of a Markdown file as an
outline. I read a lot of long notes and want to see their skeleton at a glance.

## What it should do

- `mdoutline NOTES.md` — prints the outline: each heading as a bullet,
  indented one level per heading depth. Heading text only, no # marks.
- `mdoutline --max-depth 2 NOTES.md` — only headings up to depth 2.
- `mdoutline --numbers NOTES.md` — prefix each entry with hierarchical section
  numbers (1., 1.1, 1.1.1, ...).
- No file argument: read stdin instead (`cat NOTES.md | mdoutline`).
- Missing file: clear error message on stderr, exit code 1. Normal runs exit 0.

## Things I care about

- It must work on real-world Markdown. In particular, # lines inside code
  fences are code, not headings — don't list them.
- ATX headings (# style) are enough; I don't need setext (=== underline).
- Python, stdlib only — no dependencies. Tests with pytest.

I don't care about the internal design, just that the CLI behaves as above.

## Implementation Decisions

Tier T1 (blast-radius rubric: one yes — a new CLI invocation surface; radius
contained to this repo). Stack: recipe `cli-tool-prototype`, toolkit
`python-cli` — Python 3 + argparse, stdlib only; see
`docs/adr/ADR-001-python-stdlib-cli.md`, which also records why the preferred
Rust CLI stack was not used (spec pins Python stdlib-only).

- Single module `mdoutline.py` at repo root; no packaging beyond what pytest
  needs. CLI surface frozen as specced: optional positional file argument
  (absent → read stdin), `--max-depth N` (keep headings with depth ≤ N),
  `--numbers`; errors to stderr, exit 1 on failure, exit 0 on success.
- Extraction: line-oriented ATX scan. A line is a heading iff it is outside a
  fenced code block, has ≤ 3 leading spaces (CommonMark tolerance), then 1–6
  `#`, then a space or end of line; a trailing `#` run is stripped only when it
  forms a closing sequence: it is preceded by a space/tab, or the run is the
  entire text after the opener's separating space (so `## C#` keeps its `#`).
  Fences open on lines whose first non-space characters are three or
  more backticks or tildes (matching char); a closing fence has the same
  fence char as the opener, a run of at least three and at least the opener's
  length, and nothing after the run but spaces or tabs (no info string); an
  unclosed fence at EOF fences to the end. Setext headings are not recognized
  (spec).
- Output shape pinned so tests are golden: bullet `- `, indent 2 spaces per
  heading depth below h1 (h1 → column 0). `--numbers` uses depth-indexed
  counters (a heading at depth d increments counter[d] and resets deeper
  counters), printed between bullet and text (`- 1. Intro`, `- 1.1 Setup`),
  computed over the headings that survive `--max-depth` filtering.

## Testing Decisions

pytest (per spec and the `python-cli` toolkit), ruff for linting; mypy skipped
— preference marks it "Optional for small CLI tools".

- Unit tests against extraction/rendering functions: fence handling (backtick
  and tilde fences, indented openers, unclosed fence at EOF), depth parsing,
  trailing-`#` stripping, ≤3-space tolerance, empty input, file with no
  headings, 7+ `#` marks (not a heading).
- CLI behaviour tests via subprocess: file argument, stdin fallback,
  `--max-depth`, `--numbers`, missing file → non-empty stderr + exit code 1,
  normal runs exit 0.

Architecture: reviewed by architect — tier T1, 2026-08-16, gate card t_bd518636
