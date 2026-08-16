# ADR-001: Python stdlib-only CLI (argparse), not the preferred Rust stack

- Status: Accepted
- Date: 2026-08-16
- Deciders: architect
- Introduced-by: t_bd518636

## Decision

Build mdoutline as a single-module Python 3 CLI using only the standard
library (argparse for the invocation surface). pytest and ruff are dev-only
tooling. No runtime dependencies.

## Context

The spec pins the implementation language and dependency budget: "Python,
stdlib only — no dependencies. Tests with pytest." The team's
tech-preferences.json ranks Rust first for CLIs, but the rust-cli path pulls
third-party crates (clap and friends) and a compiled toolchain, both excluded
by the spec constraint. The preference file's own sanctioned recipe for this
case is `cli-tool-prototype` → toolkit `python-cli` (python3, argparse, pytest,
ruff), which fits the constraint exactly.

## Alternatives Considered

- Rust + clap (`cli-tool` recipe, the preferred CLI stack): rejected — violates
  the spec's Python stdlib-only constraint; a personal note-reading utility
  gains nothing from a compiled toolchain.
- click/typer: rejected — third-party, violates stdlib-only.
- mypy added to the toolkit: skipped — preference marks it optional for small
  CLI tools.

## Consequences

- Zero dependency lock-in; the tool ships as one portable script.
- argparse covers the flat flag surface (--max-depth, --numbers); no
  subcommands are specced or anticipated.
- Adding any runtime dependency later is a new decision and supersedes this
  ADR.

## Citations

- spec `docs/specs/mdoutline.md` (spec card t_24a9ebca) — "Python, stdlib only
  — no dependencies. Tests with pytest."
- preferences `~/.hermes-teams/startup/tech-preferences.json` (rust tool,
  when_to_use) — "Top priority for everything possible. Performance-critical
  code, WASM targets, systems tools, CLIs, servers."
