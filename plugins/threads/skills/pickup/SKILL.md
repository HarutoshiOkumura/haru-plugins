---
name: pickup
description: Start a session on a thread (a long-running workstream in docs/threads/) by loading its SPEC, STATUS and recent LOG, checking what changed since the last handoff, and saying where to start. Use when the user says to pick up, continue, resume or get back to a piece of work, or names a thread.
argument-hint: "[thread-slug]"
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" *), Bash(git status *), Bash(git log *), Bash(git diff *), Bash(gh issue view *), Bash(gh pr view *), Bash(gh pr list *)
---

# Pick up a thread

Arguments: $ARGUMENTS

## Facts gathered when this skill loaded

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" context`

## Steps

1. **Choose the thread.**
   Use the slug from the arguments if one was given.
   Otherwise use `branch_thread` from the facts.
   Otherwise, if exactly one thread is open, use it; if several are, ask the user which one, listing each with its summary.
   If `docs/threads/` is missing, say the repo is not set up for threads, suggest `/threads:setup`, and stop.
   If the slug matches no open thread, say so, list the open threads (and the archived one if it matches), and stop.

2. **Read the thread.**
   Read `SPEC.md` and `STATUS.md` in full, and the first 100 lines of `LOG.md` (newest entries are on top).
   Read `notes.md` only where STATUS points to it for the next step.
   Read the ADRs listed under SPEC "Related" when they bear on the next step.
   If the session-start message already showed STATUS.md and nothing has changed it since, do not read it again.

3. **Check the docs against reality.**
   STATUS.md was true when it was written; the code may have moved since.
   - `git log --oneline -n 30 --since=<STATUS updated date>`: commits after the last handoff. Work on this thread that the newest LOG entry does not mention was done without a handoff; summarize it.
   - `git status --short`: uncommitted changes, and whether they match what STATUS says is in progress.
   - If STATUS or SPEC has an `issue:` link and `gh` works, read new issue comments (`gh issue view <number> --comments`).
   - If the branch has an open pull request, read its review comments (`gh pr view --comments`).
   Skip the `gh` checks quietly when `gh` is missing or not signed in.

4. **Report** in at most 15 lines:
   - Goal: one line from SPEC.
   - Where things stand: from STATUS, corrected by step 3.
   - Changed since the last handoff, or "nothing".
   - Do-not-retry items that bear on the next step.
   - Open questions that block the next step.
   - The next step, concrete enough to start now.

   Then, if the user's message already asks for specific work, start on it.
   Otherwise ask whether to start on the next step.

5. **Stay on this thread.**
   Treat it as the session's thread until the user says otherwise.
   If the work drifts into another thread, say so and suggest `/threads:handoff` followed by `/clear`, so each session holds one thread.
   If the branch does not map to this thread and code changes are coming, suggest a branch named `<slug>/<topic>` (or `claude -w <slug>` for a parallel worktree), so later sessions load the thread on their own.
   Do not create branches or worktrees without the user's go-ahead.
