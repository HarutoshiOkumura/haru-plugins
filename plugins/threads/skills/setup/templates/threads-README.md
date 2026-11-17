# Threads

A thread is a workstream that spans several sessions: a feature, a migration, an investigation.
Each thread has a folder `docs/threads/<slug>/`:

- `SPEC.md`: goal, scope, and what "done" means. Changes rarely, and each change is noted in LOG.md.
- `STATUS.md`: the current truth: where things stand, next steps, open questions, approaches not to retry. Rewritten at every handoff and kept under 80 lines.
- `LOG.md`: dated history, newest first. Entries are never rewritten.
- `notes.md`: scratch findings and research.

Finished threads move to `_archive/`.

## Session routine

1. Start: read the thread's STATUS.md, then SPEC.md and the top of LOG.md as needed.
2. Work on that thread only. Switch threads with a new session.
3. End: rewrite STATUS.md to the current truth, add a LOG.md entry, and commit both.

## Naming

Name branches `<slug>/<topic>` (for example `auth-rewrite/token-refresh`), or start a parallel worktree with `claude -w <slug>`.
With the threads plugin, a session on such a branch loads the thread's STATUS.md automatically.

## The threads plugin

The plugin automates the routine: `/threads:pickup`, `/threads:handoff`, `/threads:new`, `/threads:close`, `/threads:adr`, `/threads:audit` and `/threads:setup`.
`/threads:help` shows a quick reference.
This repo's `.claude/settings.json` enables it.
Install it once per machine:

```sh
claude plugin marketplace add HarutoshiOkumura/haru-plugins
claude plugin install threads@haru-plugins
```

Without the plugin, follow the routine above by hand; the file formats are the same.
