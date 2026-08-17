# mdoutline

Markdown outline extractor — see a document's heading skeleton at a glance.
Built end-to-end by an autonomous multi-agent pipeline from a plain user spec.

```console
$ mdoutline NOTES.md
- Title
  - Alpha
    - Deep
  - Beta

$ mdoutline --max-depth 2 NOTES.md
- Title
  - Alpha
  - Beta

$ mdoutline --numbers NOTES.md
- 1. Title
  - 1.1 Alpha
    - 1.1.1 Deep
  - 1.2 Beta

$ cat NOTES.md | mdoutline          # stdin when no file
```

## Install

```console
$ pip install .
$ mdoutline --help
```

Or without installing: `python mdoutline.py NOTES.md`. Python 3.9+,
standard library only.

## Behavior contract

| Case | Result |
|---|---|
| file argument | indented bullet outline, one level per heading depth, exit 0 |
| `--max-depth N` | headings deeper than N omitted, exit 0 |
| `--numbers` | hierarchical section numbers (1., 1.1, 1.1.1) |
| no argument | reads stdin, exit 0 |
| missing file | `mdoutline: cannot read '<f>': ...` on stderr, exit 1 |
| `#` lines inside code fences | code, not headings — never listed |
| heading with empty text | no trailing whitespace artifact |

ATX headings (`#` style) only. Tests pin real-world edges: code-fence
exclusion, stdin/UTF-8/BOM handling, broken-pipe silence (exit 141),
deployment realism (suite green with the venv off PATH; runner falls back
to `python -m` under a foreign interpreter).

## Tests

```console
$ pip install pytest && pip install -e .
$ pytest
```

## Provenance

Entirely produced — code, tests, docs, commits — by an autonomous
multi-agent pipeline (product-owner → architect → tech-lead → developer →
verifier, with adversarial verification, milestone QA and an automated
refactor cycle) from a one-page user spec. The commit history is the
unedited record of that run; every defect the verifiers found (broken-pipe
traceback, BOM handling, empty-heading whitespace, stdin decode errors,
hardcoded test paths) was caught and fixed inside the run itself.

Spec: [docs/specs/mdoutline.md](docs/specs/mdoutline.md).

## License

MIT — see [LICENSE](LICENSE).
