---
name: close
description: Finish a thread. Checks its done criteria, moves lasting lessons into area CLAUDE.md files, rules, ADRs or the architecture doc, archives the folder to docs/threads/_archive/, and optionally closes its GitHub issue.
argument-hint: "<thread-slug> [done|abandoned|superseded]"
disable-model-invocation: true
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" *), Bash(git status *), Bash(git log *), Bash(git diff *), Bash(gh issue view *)
---

# Close a thread

Arguments: $ARGUMENTS

## Facts gathered when this skill loaded

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" context`

## Steps

1. **Choose the thread** from the arguments, else `branch_thread`, else ask.
   Read its SPEC.md, STATUS.md, LOG.md and notes.md in full.

2. **Settle the outcome.**
   Check each "Done means" item against the code, running the checks it names.
   The outcome is `done`, `abandoned`, or `superseded` (by which thread).
   If the user asked for `done` but items are unmet, list them and ask how to proceed.

3. **Keep what lasts.**
   Go through STATUS.md (Do not retry, Gotchas) and LOG.md (Decided, Failed, Verified).
   Pick the facts that stay true of the code after this thread and will matter to later work.
   Leave out facts that are only history; the archive keeps them.
   Put each one where later sessions will see it:
   - a fragile part or gotcha of one area: that area's `CLAUDE.md`, with its `Last verified` date updated;
   - a convention that cuts across areas: the root `CLAUDE.md`, or `.claude/rules/<topic>.md` scoped with `paths:`;
   - a decision still in force without an ADR: a new ADR, following the `/threads:adr` steps;
   - a change to the system's structure: `docs/architecture.md`.

   Show the list of proposed additions before editing, one line each, and apply the ones the user accepts.

4. **Write the final state.**
   STATUS.md: `state` is the outcome, `updated` is today, `summary` states the result, and "Where things stand" says what shipped (pull requests, commits) and what did not.
   LOG.md: a top entry `## <date> - Closed: <outcome> (<author>)`.

5. **Archive.**
   `git mv docs/threads/<slug> docs/threads/_archive/<slug>`.
   Search the repo for `docs/threads/<slug>` and update those links to the archive path.

6. **Close the issue** only if the user agrees: comment with the outcome and the pull requests, then close it with `gh issue close`.

7. **Commit** the edited and moved files, by path, with the message `docs(<slug>): close thread (<outcome>)`.
   Skip the commit only if the user asked not to commit these docs, or a merge or rebase is in progress.
   Do not push unless the user asks.

8. **Reply** with the outcome, where each lasting lesson went, and the archive path.
