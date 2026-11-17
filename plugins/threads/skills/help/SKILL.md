---
name: help
description: Show the threads workflow quick reference (commands, session routine, where project memory lives, worktrees, teammates) and the current repo's thread state, or answer a question about how the threads plugin works. Use when the user asks for threads help, or asks how the thread docs, handoffs or this workflow work.
argument-hint: "[question or topic]"
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" *)
---

# Threads help

Arguments: $ARGUMENTS

## Facts gathered when this skill loaded

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" context`

## What to do

This skill only reads; it changes nothing.

- **No arguments:** reply with the card between the `CARD START` and `CARD END` lines below, exactly as written, without the marker lines and without adding anything inside it. Then add the "This repo" section described below.
- **A question or topic:** answer it in a few lines. Use the card, and for detail read `${CLAUDE_PLUGIN_ROOT}/README.md` and the relevant `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`. Do not print the whole card. End with the "This repo" section only if it bears on the answer.

**"This repo" section**: at most 6 lines, built from the facts:

- If `threads_dir` is missing: the repo is not set up; `/threads:setup` sets it up.
- Otherwise: the branch and its thread (or that no thread matches it), the open threads with their state and how long ago each was updated, and anything that needs attention: active threads not updated for over 21 days, threads closed but not archived, or uncommitted changes.
- End with the single most useful next command for this repo.

CARD START

## threads: quick reference

| Command | Use it when |
|---|---|
| `/threads:pickup [slug]` | Starting a session. Automatic on a thread's branch |
| `/threads:handoff` | Ending a session, or before `/clear` or `/compact` |
| `/threads:new <slug>` | Starting work that will span several sessions |
| `/threads:adr <title>` | A decision crosses threads or areas, or could be reversed by someone who does not know why |
| `/threads:close <slug>` | A thread is finished, abandoned or superseded |
| `/threads:audit` | Now and then, to find and fix stale docs |
| `/threads:setup` | Once per repo |
| `/threads:help [question]` | This card, or an answer about the workflow |

**A session**

1. Start on the thread's branch (`<slug>/<topic>`), or in its worktree (`claude -w <slug>`): STATUS.md loads by itself. On `main`, run `/threads:pickup <slug>`.
2. One thread per session. To switch: `/threads:handoff`, then `/clear`.
3. For wide searches ("everything that touches X"), ask for a subagent.
4. To compact by hand, say what to keep: `/compact keep <what matters>`. Automatic compaction keeps unsaved work and reloads STATUS.md.
5. Before closing the terminal: `/threads:handoff`.

**Where project memory lives**

| File | Holds | Loaded |
|---|---|---|
| `CLAUDE.md` | Purpose, map, commands, conventions. Under 150 lines | Every session |
| `<area>/CLAUDE.md` | Area quirks, fragile parts, owner, `Last verified` | When working in that folder |
| `.claude/rules/*.md` | Cross-cutting rules, scoped with `paths:` | When working on matching files |
| `docs/architecture.md` | The big picture | On demand |
| `docs/decisions/` | ADRs: never edited, only superseded | On demand |
| `docs/threads/<slug>/` | One workstream | Its STATUS.md at session start on its branch |
| `~/.claude/CLAUDE.md` | Your personal preferences | Every session, yours only |

**Inside a thread**

- `SPEC.md`: goal, scope, what "done" means. Rarely changes.
- `STATUS.md`: current truth, next steps, open questions, do-not-retry list. Rewritten at each handoff, under 80 lines. State: active, paused, blocked, done, abandoned or superseded.
- `LOG.md`: dated history, newest first. Never rewritten.
- `notes.md`: scratch findings.
- Finished threads move to `docs/threads/_archive/`.

**Parallel threads**: one worktree and session per thread. `claude -w <slug>` makes `.claude/worktrees/<slug>/` on the branch `worktree-<slug>`, which loads that thread.

**Teammates**, once per machine: trust the repo folder when asked, then run `claude plugin marketplace add HarutoshiOkumura/haru-plugins` and `claude plugin install threads@haru-plugins`.

**Full docs**: `${CLAUDE_PLUGIN_ROOT}/README.md`

CARD END
