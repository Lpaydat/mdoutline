# Issue Tracker: bd (beads)

Issues for this repo live in **bd (beads)** — a local Dolt database under `.beads/` (embedded mode, no server). Not GitHub Issues, not markdown files. `.beads/issues.jsonl` is a passive export, never the source of truth.

## Workflow

```bash
bd create --title="..." --description="..." --type=task|bug|feature --priority=2
bd ready                          # unblocked, ready to work
bd list --status open,in_progress,blocked
bd show <id>                      # details + dependencies
bd update <id> --claim            # claim atomically
bd close <id> --reason="..."      # complete
bd dep add <id> <depends-on-id>   # dependency edge
bd update <id> --add-label <role> # triage label
bd search <query>
```

- IDs look like `mdoutline-q56`, `mdoutline-47y`.
- Statuses: `open`, `in_progress`, `blocked`, `done`. `bd close` is the only completion path; confirm every close with a `bd show` read afterwards.
- Cross-machine sync: `bd dolt push` / `bd dolt pull` (stored under `refs/dolt/data` on the git remote — separate from `refs/heads/*`).
- Persistent knowledge: `bd remember "<insight>"`, not MEMORY.md files.
