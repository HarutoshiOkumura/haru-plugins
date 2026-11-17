# threads

Project memory for multi-month work with Claude Code.

Claude Code starts every session knowing nothing, so a long project's memory has to live in the repo.
The `threads` plugin gives every repo the same layered structure, the commands to keep it current, and hooks that load the right part of it automatically.
Because the memory is in the repo, teammates' sessions share it.

For a one-screen summary inside Claude Code, run `/threads:help`.

## The layers

| Layer | File | Holds | Loaded |
|---|---|---|---|
| Personal | `~/.claude/CLAUDE.md` | Your own preferences, kept out of the repo | Every session |
| Root | `CLAUDE.md` | Purpose, map of areas, commands, conventions, pointers. Under 150 lines. No status or history | Every session |
| Area | `<area>/CLAUDE.md` | The area's quirks, fragile parts, owner, and a `Last verified` date | When Claude works in that folder |
| Cross-cutting rules | `.claude/rules/<topic>.md` with `paths:` | Rules for files spread across areas | When Claude works on matching files |
| Big picture | `docs/architecture.md` | Components, data flow, invariants | On demand |
| Decisions | `docs/decisions/NNNN-*.md` | ADRs: never edited, only superseded | On demand, through the index |
| Workstreams | `docs/threads/<slug>/` | `SPEC.md`, `STATUS.md`, `LOG.md`, `notes.md` | The branch's STATUS at session start; the rest on demand |

A thread folder looks like this:

```
docs/threads/auth-rewrite/
  SPEC.md     goal, scope, what "done" means; changes rarely
  STATUS.md   current truth: where things stand, next steps, open questions, do-not-retry list; rewritten at every handoff, under 80 lines
  LOG.md      dated history, newest first; never rewritten
  notes.md    scratch findings and research
docs/threads/_archive/   finished threads
```

## Commands

| Command | When |
|---|---|
| `/threads:setup` | Once per repo: writes the root and area `CLAUDE.md` files, `docs/architecture.md`, `docs/decisions/`, `docs/threads/`, a PR template, and the settings that turn the plugin on for teammates. Moves status and history out of an existing `CLAUDE.md` without losing any of it |
| `/threads:new <slug>` | Starting a workstream that will take more than a couple of sessions. Drafts the SPEC, and offers a GitHub issue and a branch or worktree |
| `/threads:pickup [slug]` | Starting a session. Reads the thread, checks what changed since the last handoff (commits, issue and PR comments), and says where to start |
| `/threads:handoff` | Before ending a session, `/clear` or `/compact`. Rewrites STATUS, adds a LOG entry, fixes any doc the session made wrong, and commits the docs |
| `/threads:adr <title>` | A decision that crosses threads or areas, or that someone might later reverse without knowing why |
| `/threads:close <slug>` | A thread is finished or abandoned. Moves lasting lessons into area files, rules or ADRs, then archives the folder |
| `/threads:audit` | Now and then. Finds broken path references, overdue `Last verified` dates, stale threads and ADR index gaps, then fixes them |
| `/threads:help [question]` | The quick reference card and the current repo's thread state, or an answer to a question about the workflow |

Claude can also start `pickup`, `handoff`, `new`, `adr`, `audit` and `help` by itself when the conversation calls for them, for example when you say "let's continue the auth rewrite" or "wrap up".
`setup` and `close` run only when you type them.

## Hooks

- **Session start** (also after `/clear`, on resume, and after compaction): on a branch that belongs to a thread, Claude gets that thread's STATUS.md. On any other branch, it gets a one-line-per-thread list of open threads. In a repo without `docs/threads/` the hook prints nothing.
- **Before compaction**: the hook tells the summarizer to keep the thread's name and everything not yet written to STATUS.md or LOG.md, and to flag a pending handoff. Right after compaction, the session-start hook loads STATUS.md again.

A branch belongs to a thread when one of its `/`-separated parts is the thread's slug: `auth-rewrite`, `auth-rewrite/token-refresh`, `haru/auth-rewrite/x`, or `worktree-auth-rewrite` (the branch `claude -w auth-rewrite` creates).

## A day with it

1. `cd` into the repo and start Claude Code on the thread's branch. The thread's STATUS.md is already loaded. On `main`, say which thread to work on, or run `/threads:pickup <slug>`.
2. Work on that thread only. When the task changes to a different thread, run `/threads:handoff`, then `/clear`.
3. For a wide search ("find everything that touches X"), ask for a subagent, so the file dumps stay out of the main context and only the conclusion comes back.
4. If the context fills up, compaction keeps what STATUS.md does not have yet. To compact by hand, say what to keep: `/compact keep the migration plan and the failing test details`.
5. Before closing the terminal, run `/threads:handoff`.

## Parallel threads

Give each thread its own worktree and session, so contexts never mix:

```sh
claude -w auth-rewrite     # worktree in .claude/worktrees/auth-rewrite/, branch worktree-auth-rewrite
claude -w billing-v2       # in another terminal
```

Or make the worktree yourself, with a branch named after the thread:

```sh
git worktree add ../myrepo-auth -b auth-rewrite/token-refresh
cd ../myrepo-auth && claude
```

Claude Code's personal auto memory is shared by all worktrees of a repo; the thread docs travel with each branch and merge back with its pull requests.

## GitHub and teammates

- **Issues for people, threads for sessions.** `/threads:new` offers a tracking issue and links the two both ways. The issue is where people coordinate; the thread is the detailed working memory.
- **PR descriptions are context too.** The PR template asks for "Decisions and why", and for a check that no doc is now wrong. Later sessions catch up on a teammate's area with `gh pr list`, `gh pr view` and `git log -- <path>`.
- **ADRs for anything that crosses threads**, so other people's sessions see the decision.
- **Teammates install the plugin once.** `/threads:setup` commits `.claude/settings.json` with the marketplace and `"threads@haru-plugins": true`. Each teammate trusts the folder when Claude Code asks, then runs `claude plugin install threads@haru-plugins`. Without the plugin, `docs/threads/README.md` explains the routine by hand.

## Keeping it from going stale

Stale context is worse than none, because Claude follows it confidently.

- Area `CLAUDE.md` files and `docs/architecture.md` carry a `Last verified` date; `/threads:audit` flags dates older than 90 days.
- `/threads:audit` (and `threads.py audit --strict` in CI) reports code-span paths in `CLAUDE.md` files, rules and the architecture doc that no longer exist.
- The session-start list shows how long ago each thread was updated, and the audit flags active threads untouched for 21 days and finished threads not archived.
- `/threads:handoff` fixes any doc the session made wrong, and `/threads:close` moves lasting lessons out of the thread before archiving it.
- The PR template asks whether the change made any doc wrong.

## Design notes

- **STATUS.md is rewritten, never appended to.** An appended status file grows into a wall of "before that" paragraphs that every later session pays to read. History goes to LOG.md, newest first, so `/threads:pickup` reads only the top.
- **"Do not retry" lives in STATUS.md**, because "we tried X and it failed because Y" is the costliest thing to lose and has to be in front of Claude before it tries X again.
- **The plugin is the single source of truth.** Skills, hooks and templates live here and are versioned, so every repo and teammate runs the same workflow; a repo can override the thread templates with `docs/threads/_template/`.
- **Skills start from facts, not guesses.** Each skill runs `threads.py context` when it loads (today's date, git author, branch, matching thread, open threads, next ADR number, uncommitted changes, merge or rebase in progress), so dates and names in the docs are exact.
- **Skills commit only the doc files they touched**, as their own commit, and never push. Code stays out of those commits.
- **The hooks never block a session.** They exit 0 on any error, stay under Claude Code's 10,000-character hook output cap, and print nothing in repos that do not use threads.
- **The help card and these docs cannot drift silently.** A test fails when a skill is missing from `/threads:help`, this README, or the `docs/threads/README.md` template.

## Requirements

The hooks need `python3` 3.8 or newer and `git` on the `PATH`; `gh` is optional, for issues and pull requests.
