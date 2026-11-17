# haru-plugins

Claude Code plugins by HarutoshiOkumura, published as a plugin marketplace.
It holds one plugin today: **threads**, project memory for multi-month work with Claude Code.

Claude Code starts every session knowing nothing, so a long project's memory has to live in the repo.
`threads` keeps that memory in layers: a little of it loads in every session, and Claude reads the rest only when a task needs it.
Its commands keep the memory current, and its hooks load the right part automatically, including right after the context is compacted.
Because the memory is in the repo, teammates' sessions share it.

## Install

```sh
claude plugin marketplace add HarutoshiOkumura/haru-plugins
claude plugin install threads@haru-plugins
```

Then start a new Claude Code session, or run `/reload-plugins` in an open one, and run `/threads:help` to check that it works.

You need Claude Code, `git`, and `python3` 3.8 or newer (the one that ships with macOS is fine).
The GitHub CLI `gh` is optional; with it, threads can create and read issues and pull requests.

## Quick start

1. **Set up a repo**, once: `cd` into it, start `claude`, and run `/threads:setup`.
   Claude surveys the repo and proposes a plan before writing anything: a short root `CLAUDE.md`, `CLAUDE.md` files for areas with non-obvious knowledge, `docs/architecture.md`, `docs/decisions/`, `docs/threads/`, a pull request template, and the settings that turn the plugin on for teammates.
   Status and history in an existing `CLAUDE.md` move into thread docs; nothing is deleted.
2. **Start a workstream**: `/threads:new auth-rewrite`.
   Claude drafts a SPEC with checkable "done means" criteria, asks only what it cannot work out, and offers a GitHub issue and a branch or worktree.
3. **Work in sessions on the thread's branch**: `git switch -c auth-rewrite/token-refresh`, or a parallel worktree with `claude -w auth-rewrite`.
   Each session on that branch starts with the thread's STATUS.md already loaded: where things stand, the next step, open questions, and approaches not to retry.
4. **End every session with `/threads:handoff`.**
   It rewrites STATUS.md to the current truth, adds a dated LOG.md entry, fixes any doc the session made wrong, and commits only those doc files.
5. **When the work is done, run `/threads:close auth-rewrite`.**
   Lasting lessons move into the area docs, rules or ADRs, and the thread is archived.

## The workflow at a glance

| When | Run | Result |
|---|---|---|
| Once per repo | `/threads:setup` | Layered project memory and team settings |
| Once per workstream | `/threads:new <slug>` | SPEC, STATUS, LOG and notes; optionally an issue and a branch or worktree |
| Start of a session | Open the thread's branch, or `/threads:pickup <slug>` | STATUS.md loaded, plus what changed since the last handoff |
| End of a session, or before `/clear` or `/compact` | `/threads:handoff` | STATUS rewritten, LOG entry added, docs committed |
| A decision others must follow | `/threads:adr <title>` | A numbered ADR that other sessions and teammates see |
| The work is finished | `/threads:close <slug>` | Lessons kept, thread archived |
| Every few weeks | `/threads:audit` | Broken references, overdue reviews and stale threads found and fixed |
| Any time | `/threads:help [question]` | A quick reference card and this repo's thread state, or an answer |

## Habits that make it work

1. **One thread per session.** To switch, run `/threads:handoff`, then `/clear`.
2. **Never end a session without `/threads:handoff`.** It is what lets the next session start in seconds.
3. **Parallel work means parallel worktrees**: one terminal and one `claude -w <slug>` per thread.
4. **Keep the main context clean.** Ask for a subagent for wide searches, and when compacting by hand say what to keep: `/compact keep the migration plan`.
5. **Define "done" before starting.** SPEC's "done means" is the contract; STATUS's first "Next" item is where to start.
6. **Write decisions where others will see them**: ADRs, and the "Decisions and why" section of each pull request.
7. **When a doc becomes wrong, fix it in the same change.** Stale context is worse than none, because Claude follows it confidently.

Avoid putting status or history in `CLAUDE.md`, relying on chat transcripts or personal memory for project knowledge, and long sessions that drift across topics.

## Working with a team

- `/threads:setup` commits `.claude/settings.json` with this marketplace and `"threads@haru-plugins": true`. Each teammate trusts the folder when Claude Code asks, then runs the two install commands above once.
- Issues are for people, thread docs are for sessions; `/threads:new` links the two both ways.
- The pull request template asks for "Decisions and why" and for a check that no doc is now wrong.
- Without the plugin, `docs/threads/README.md` in a set-up repo explains the routine by hand.

## Documentation

- [`plugins/threads/README.md`](plugins/threads/README.md): the full reference (layers, commands, hooks, worktrees, staleness checks, design notes).
- `/threads:help` inside Claude Code: a one-screen card and the current repo's state.
- `docs/threads/README.md` in each set-up repo: the thread format for people without the plugin.

## Developing

This repo uses its own workflow: [`CLAUDE.md`](CLAUDE.md) holds the conventions, and [`docs/threads/`](docs/threads) holds the work in progress.

Install from a local clone instead of GitHub, so your edits apply at the next session start or after `/reload-plugins`:

```sh
git clone https://github.com/HarutoshiOkumura/haru-plugins.git
claude plugin marketplace add ./haru-plugins       # if the GitHub marketplace is already added, first run: claude plugin marketplace remove haru-plugins
claude plugin install threads@haru-plugins
```

Checks, all run in CI except the validator:

```sh
python3 -m unittest discover -s tests                       # unit tests
uvx ruff check . && uvx ruff format --check .               # lint and format
claude plugin validate . && claude plugin validate plugins/threads
python3 plugins/threads/scripts/threads.py audit            # this repo's own docs
```

Try a change in one session without installing it: `claude --plugin-dir plugins/threads`.

```
.claude-plugin/marketplace.json     the marketplace: lists the plugins
plugins/threads/
  .claude-plugin/plugin.json        name, version, license
  hooks/hooks.json                  SessionStart and PreCompact, both call threads.py
  scripts/threads.py                hook output, facts for skills, docs audit (standard library only)
  skills/<name>/SKILL.md            one folder per slash command, with its templates
  README.md                         full reference
tests/test_threads.py               unit tests, including a check that every command is documented
```

To add a command, create `plugins/threads/skills/<name>/SKILL.md` (its `name` must match the folder) and list it in the help card, both READMEs and `skills/setup/templates/threads-README.md`; the tests fail until it is in all of them.

To release, raise `version` in `plugins/threads/.claude-plugin/plugin.json` (people who installed from GitHub only get changes when it changes), commit, then run `claude plugin tag plugins/threads` and `git push --follow-tags`.

## License

[MIT](LICENSE)
