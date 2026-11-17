---
thread: rollout
state: active
summary: Built and tested; publishing to GitHub, then a first real repo
updated: 2026-11-17
issue: none
---

# Rollout: status

Rewritten at every handoff: current truth only, history goes in LOG.md.
Keep it under 80 lines.

## Where things stand

- Plugin version 0.1.0: 8 skills (setup, new, pickup, handoff, adr, close, audit, help), SessionStart and PreCompact hooks, and `threads.py` (hook output, skill facts, docs audit).
- Verified 2026-11-17: unit tests pass on Python 3.14; vermin reports 3.8 as the minimum version; ruff is clean; `claude plugin validate` passes.
- Verified 2026-11-17 end to end with headless sessions in a scratch repo: session-start injection, `/threads:pickup`, `/threads:handoff` (commits only the docs), `/compact` (the summary names the thread and STATUS.md is loaded again), and `/threads:help` in card and question modes.
- The maintainer's machine runs it from the local clone (a directory marketplace), so edits apply at the next session or `/reload-plugins`.
- Not on GitHub yet when this was written.

## Next

1. Create the public repo `HarutoshiOkumura/haru-plugins`, push, and confirm both CI jobs pass. The macOS job is the first run on macOS's system python3.
2. Choose the first real repo and run `/threads:setup` in it.
3. Install from GitHub on a machine or account without the local clone, following the root README.

## Open questions

- Which repo is the first pilot?
- Submit to the plugin directory later? It needs a square PNG icon, 512 to 2048 px.

## Do not retry

- Handoff commit rule worded "unless the user said not to": a session read an earlier "do not commit" about code as covering the docs, and skipped the doc commit (2026-11-17). The rule now names the docs explicitly.

## Gotchas

- A `claude --plugin-dir` session replaces the installed plugin of the same name for that session.
- Installs from GitHub only update when `version` in `plugin.json` changes.
- In headless test runs, put the prompt after `--` when passing `--allowedTools`, or the prompt is read as a tool name.
- `claude plugin validate --strict` wants a marketplace description and a plugin version; the directory profile also wants a license (MIT, added).
