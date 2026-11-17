---
name: new
description: Start a new thread, a workstream that will span several sessions, with SPEC, STATUS, LOG and notes in docs/threads/<slug>/, plus an optional GitHub issue and branch or worktree. Use when the user wants to start a new long-running piece of work such as a feature, migration, rewrite or investigation.
argument-hint: "<slug> [goal]"
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" *), Bash(git status *), Bash(git log *), Bash(git remote *)
---

# Start a thread

Arguments: $ARGUMENTS

## Facts gathered when this skill loaded

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" context`

## Steps

1. **Check preconditions.**
   If `docs/threads/` is missing, suggest `/threads:setup` and stop.
   The slug is kebab-case, at most 30 characters, and specific (`auth-rewrite`, not `auth`).
   If no slug was given, propose one from the goal.
   It must not match an open, closed or archived thread from the facts.

2. **Understand the work.**
   Read the root `CLAUDE.md`, `docs/architecture.md`, the ADR index in `docs/decisions/README.md`, and the `CLAUDE.md` of each area the work touches.
   For wide questions such as "what touches X?", use an Explore subagent so the file dumps stay out of this context.
   Check whether an open thread already covers part of this work.

3. **Draft the spec, then ask once.**
   Draft SPEC.md from what the user said and what you found.
   Then ask, in a single round, only what you cannot infer: the goal, checkable "done means" criteria, what is out of scope, and hard constraints.
   Show the draft goal and done-means for confirmation.

4. **Set up where the work will happen.**
   Ask whether the user wants one of these, and create it only on a yes:
   - a branch in this checkout: `git switch -c <slug>/<topic>`;
   - a parallel worktree, for working on several threads at once: the user runs `claude -w <slug>` (worktree in `.claude/worktrees/<slug>/` on the branch `worktree-<slug>`), or `git worktree add ../<repo>-<slug> -b <slug>/<topic>`.

   Branch names that contain the slug as a `/`-separated segment load this thread at session start.
   If a branch is created here, switch to it before step 5, so the thread docs are committed with the thread's work.

5. **Create the folder.**
   Copy the templates from `${CLAUDE_SKILL_DIR}/templates/` into `docs/threads/<slug>/`.
   If the repo has its own `docs/threads/_template/`, use that instead.
   Fill every `{placeholder}`: dates are `today`, the author and owner are `author` from the facts, and STATUS starts with `state: active` and a concrete first step under Next.
   Delete template sections that have nothing to say yet rather than leaving placeholders.
   The first LOG.md entry records why the thread was started.

6. **Link related work.**
   If the thread overlaps another open thread, add each to the other's SPEC "Related" section.
   List relevant ADRs under "Related".

7. **Offer a tracking issue.**
   If the repo is on GitHub and `gh` works, ask whether to create an issue for people to coordinate on.
   On a yes: `gh issue create --title "<goal>" --body "<goal, done means, and a link to docs/threads/<slug>/>"`, then put the issue URL in the `issue:` field of SPEC.md and STATUS.md.

8. **Commit.**
   Stage `docs/threads/<slug>/` and any SPEC files changed in step 6, by path, and commit with the message `docs(<slug>): start thread`.
   Skip the commit only if the user asked not to commit these docs, or a merge or rebase is in progress.
   Do not push unless the user asks.

9. **Reply** with the folder path, the first step, and how to resume later: `/threads:pickup <slug>`, or a session on the thread's branch.
