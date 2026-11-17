---
name: handoff
description: Save this session's progress into the active thread's STATUS.md and LOG.md, and fix any project doc the session made wrong, so the next session or a teammate can continue cold. Use before ending a session, before /compact or /clear, when switching threads, or when the user says wrap up, hand off, save progress or checkpoint.
argument-hint: "[thread-slug] [note]"
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" *), Bash(git status *), Bash(git log *), Bash(git diff *)
---

# Hand off

Arguments: $ARGUMENTS

## Facts gathered when this skill loaded

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" context`

## How to write

- Write for a reader with no memory of this session, possibly weeks from now: a later session, or a teammate's.
- Facts, not narrative. Short sentences. Exact names of files, functions, commands and tests, exact error messages, measured numbers.
- Never claim more than happened. If something was not verified, write "not verified".
- Name who made each choice ("the user decided", "Claude chose, not yet confirmed"); never write "I" or "my", since many sessions and people share these files.
- Use absolute dates (`today` from the facts), never "today" or "yesterday".

## Steps

1. **Choose the thread.**
   Use the slug from the arguments, else the thread this session picked up or worked on, else `branch_thread`.
   If the session's work fits no thread, ask whether to start one (`/threads:new`) or skip the handoff.
   If the session touched several threads, hand off each one separately.

2. **Collect what happened.**
   From the conversation, plus `git status --short`, `git diff --stat`, and `git log --oneline` since the STATUS `updated` date.
   List: what changed, what was verified and how (tests run, results), decisions and their reasons, approaches that failed and why, new open questions, answered questions, and what comes next.
   If a plan was agreed this session, its unfinished steps belong in Next.

3. **Rewrite STATUS.md.**
   Rewrite it to the current truth; do not append to it.
   - Frontmatter: `updated` is today; `state` is current; `summary` is one line under 100 characters for the thread list.
   - Where things stand: delete lines that are no longer true. Name uncommitted work and where it lives (branch, worktree), because another session may not see it.
   - Next: ordered; the first item is concrete enough to start cold (files, commands, test names).
   - Open questions: add new ones; remove answered ones and record the answer in LOG.
   - Do not retry: add each failed approach worth not repeating, as `- <approach>: <why it failed> (<date>)`. Remove an item only when it is no longer true.
   - Keep it under 80 lines. Move detail into `notes.md` and point to it.

4. **Add a LOG.md entry** directly under the file's header, above older entries:

   ```markdown
   ## <date> - <short title> (<author>)

   - Done: ...
   - Verified: ...
   - Decided: ... because ...
   - Failed: ... because ...
   - Commits: <short sha> <subject>; PR #<n>
   ```

   Leave out empty lines. Several sessions on one day get separate entries.

5. **Carry effects beyond the thread.**
   - A decision that affects other threads or areas, or that someone might later reverse without knowing why: offer to record an ADR with `/threads:adr`.
   - A root or area `CLAUDE.md`, a `.claude/rules/` file, or `docs/architecture.md` that this session made wrong: fix it now, and update its `Last verified` date.
   - A lasting lesson about an area (a fragile part, a gotcha): add it to that area's `CLAUDE.md` as well, not only to the thread.
   - Scope that moved: update `SPEC.md` and say so in the LOG entry.

6. **Check for done.**
   If every "Done means" item in SPEC.md is met, say so and suggest `/threads:close`.

7. **Commit the docs.**
   Stage only the doc files this handoff edited, by path (never `git add -A` or `git add .`), and commit them with the message `docs(<slug>): handoff <date>`.
   Skip the commit only if the user asked not to commit these docs, or a merge or rebase is in progress (see the facts).
   An earlier request not to commit code does not cover these docs: leave the code out of this commit, as STATUS.md already names it as uncommitted.
   Do not push unless the user asks.

8. **Reply** in at most 6 lines: what was recorded, the next step, and anything the user must decide.
