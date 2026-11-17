---
thread: rollout
created: 2026-11-17
owner: HarutoshiOkumura
issue: none
---

# Rollout

## Goal

The threads plugin is public on GitHub, installs cleanly from there, and is in daily use on at least one real multi-month repo.

## Why

The plugin was built and tested against a scratch repo on 2026-11-17.
Its value, and its rough edges, only show in real sessions on real projects.

## Scope

- Publish this repo (public, MIT) with CI.
- Set up a first real repo with `/threads:setup` and run real sessions in it.
- Fix what real use reveals, in the plugin rather than in the pilot repo.
- Check the install path a teammate would take.

## Not in scope

- Submitting to the Claude Code plugin directory (it also needs an icon).
- Further plugins in this marketplace.

## Done means

- [ ] The repo is public on GitHub and both CI jobs (Linux, macOS system python3) pass.
- [ ] `claude plugin marketplace add HarutoshiOkumura/haru-plugins` and `claude plugin install threads@haru-plugins` work on a machine or account without the local clone.
- [ ] A real repo is set up with `/threads:setup`, and one of its threads has been handed off across at least 3 sessions.
- [ ] Every problem found in that use is fixed, or recorded in this STATUS.md.

## Constraints

- `threads.py` stays standard-library Python 3.8+, and the hooks never block a session.

## Related

- "Design notes" in `plugins/threads/README.md`.
