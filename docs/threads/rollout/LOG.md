# Rollout: log

Newest first.
One entry per session that changed something.
Old entries are never rewritten; add a correction in a new entry instead.

## 2026-11-17 - Plugin built and tested; repo prepared for GitHub (HarutoshiOkumura)

- Done: built the threads plugin (8 skills, 2 hooks, `threads.py`, templates), unit tests, CI, READMEs, MIT license, and this repo's own CLAUDE.md and thread docs.
- Verified: unit tests, ruff, `claude plugin validate`, and headless end-to-end sessions in a scratch repo for session start, pickup, handoff, compaction and help.
- Decided: one marketplace repo is the single source of truth for skills, hooks and templates; STATUS.md is rewritten at each handoff and history goes to LOG.md; explicit semver releases; public repo under MIT. Reasons are under "Design notes" in `plugins/threads/README.md`.
- Failed: the first handoff commit wording (see "Do not retry" in STATUS.md). The root CLAUDE.md template was named `CLAUDE.md`, which Claude Code would load as instructions inside this repo; renamed to `root-CLAUDE.md`.
- Checked before publishing: no secrets (detect-secrets), no local paths or usernames, and no references to other projects in the uploaded files.
