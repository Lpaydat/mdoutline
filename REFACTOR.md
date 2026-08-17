# REFACTOR.md — mdoutline refactor candidates (validated)

Validated against current main (repo: this repository).
All candidates below passed independent reviewer verification with executed
evidence. Suite baseline at time of validation: 263/263 tests green,
`make check` green.

Context: 2,937 test LOC vs 317 production LOC. The test suite grew one
behavior suite per ticket (dev + verifier facets), each hand-rolling its own
CLI-probe plumbing with no shared seam.

---

## C1 — Five hand-rolled CLI-probe adapters, no shared seam [Strong]

**Problem.** Each test file defines its own, subtly different subprocess
adapter for invoking the CLI:

- `tests/test_cli.py:10` — `_run_mdoutline`: `-m`, PYTHONPATH, NO timeout
- `tests/test_behavior.py:21` — `run_cli`: `-m`, PYTHONPATH, timeout=120
- `tests/test_behavior_depth.py:69-88` — `_cli`/`run_cli`: MDOUTLINE_BIN →
  `which` → `-m` fallback, NO PYTHONPATH, timeout=120
- `tests/test_behavior_numbers.py:67-86` — byte-identical copy of depth's
  block
- `tests/test_behavior_numbers_verify.py:41-68` — `run_module`/`run_console`
  hardcoding `.venv/bin/mdoutline`

Plus ~7 inline invocation sites beyond the named adapters. The divergence is
not cosmetic: `test_behavior_depth.py:394` hard-asserts the console script is
on PATH while `test_behavior_numbers.py:417,431` skip-with-reason on the
identical condition — same situation, opposite policy, in byte-identical
copied files. Two beads reproduce live at current main when the venv is not
on PATH (3 failures: 2× `which`→None assert, 1× bare /usr/bin/python rc=2
"Unknown option: --max-depth").

**Solution.** Add `tests/conftest.py` (does not exist today) with one shared
console-script resolution + subprocess runner seam:

- Env override: `MDOUTLINE_BIN` wins if set (whole command, shlex-split).
- Console-script discovery via `sysconfig.get_path('scripts')` under the
  active interpreter (NOT `Path(sys.executable).parent` + `.resolve()` —
  wrong when the venv python is symlinked).
- `-m mdoutline` fallback for foreign-cwd invocation via PYTHONPATH.
- Shared timeout policy (120s) and one tmp-file writer fixture.

Policy unification decision needed: depth's assert-script-on-PATH vs
numbers' skip-with-reason must converge on one policy (recommend: skip with
reason when the script is absent, assert once in a dedicated
script-installed test). A 9/9 execution-proven prototype of this seam
exists from the reviewer (/tmp/hermes-verify-c1-seam/proto_seam.py pattern).

**Expected yield.** ~150+ LOC of plumbing deduped; kills both live PATH
beads; makes the policy visible in one file instead of five.

---

## C2 — Cross-suite probe duplication: share plumbing, not expectations [Worth exploring]

**Problem.** The same edge-input probes (unclosed fence ×5, BOM ×4,
missing-file ×4, broken-pipe ×3, CRLF ×3, seven-hashes ×3, trailing-hashes
×3) recur across the five behavior suites. Naive dedupe looks tempting.

**Solution (calibrated — the scanner's original fix was miscalibrated).**
The original "dedupe any probe asserted identically in 3+ files" rule is
REJECTED by review: the 3+-file occurrences are cross-facet by design —
library API (`test_mdoutline.py:76`), plain CLI (`test_behavior.py:147`),
CLI×--max-depth (`test_behavior_depth.py:269`), CLI×--numbers dev
(`test_behavior_numbers.py:244`), CLI×--numbers verifier
(`test_behavior_numbers_verify.py:286`) each assert a *different observable
output* for the same input. Collapsing them would lose layer and composition
coverage. The genuinely duplicated pairs are 2-file dev-vs-verifier suites
per ticket, which are load-bearing per the verify-suite independence
doctrine (expected outputs hand-derived, not copied — declared in
`test_behavior_numbers_verify.py:1-8`).

**Actionable scope = C1's conftest only**: the subprocess runner, tmp-file
writer, and script-path helper (~100-150 LOC, ~4-5% of test LOC). Do not
share expected outputs. Optional cosmetic: ticket-03's dev CLI tests landed
in `test_behavior_numbers.py` instead of accreting into `test_cli.py` per
the t1/t2 convention — normalize or accept, zero coverage impact.

**Note.** If C1 is ticketed, C2's actionable scope is fully contained in it;
ticket them together or fold C2 into C1's ticket.

---

## C3 — Dead ruff config block in pyproject.toml (fixed by ticket-refactor-02) [Worth exploring]

**Problem.** `pyproject.toml` originally carried a `[tool.ruff]` + `[tool.ruff.lint]`
block (line-length=100, target-version=py311, select=[E,F,W,I,UP,B,SIM],
ignore=[E501]). Ruff never read it: `ruff.toml:1-9` is a strict superset
(identical values plus `[lint.isort] known-first-party=["mdoutline"]`) and
ruff's documented discovery order resolves Settings path to `ruff.toml`.
Verified empirically: mangling the pyproject block changed nothing —
`ruff check .` stayed green, effective line_length stayed 100. Simulated
deletion → full `make check` green.

**Solution.** Delete the dead block. Pure deletion, zero behavior change,
small payoff, zero risk. The reverse consolidation (move `[lint.isort]` into
pyproject, delete ruff.toml) is equally valid; keeping ruff.toml is the safer
minimal diff since it is the file actually in effect. Fine standalone as a
trivial ticket or bundled with C1/C2.

---

## Ordering

C1 (Strong) → C2 (folded into C1) → C3 (trivial, independent).

All three validated; none dropped. Original scan severity held on review
(C2 and C3 confirmed at Worth exploring; C1 confirmed at Strong).
