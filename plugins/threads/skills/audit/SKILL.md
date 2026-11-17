---
name: audit
description: Check the project's docs for Claude for staleness and fix what is wrong. Covers broken path references in CLAUDE.md files, rules and the architecture doc, files past their last-verified date, threads not updated in weeks, finished threads not archived, gaps in the ADR index, and commands that no longer exist. Use when the user asks to audit, check or clean up project docs.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" *), Bash(git status *), Bash(git log *), Bash(git diff *)
---

# Audit the project docs

Stale context is worse than none, because Claude follows it confidently.

## Facts gathered when this skill loaded

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" context`

## Mechanical checks

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" audit`

## Steps

1. **Fix each ERROR.**
   A missing path usually moved or was deleted.
   Find where it went (`git log --oneline --diff-filter=DR -- <path>`, or a search for its name) and update the reference, or delete the line if the thing is gone.

2. **Check commands.**
   For each command in the root `CLAUDE.md` "Commands" section and in area files, confirm that the script, target or tool it names still exists (`package.json` scripts, `pyproject.toml`, `Makefile`, `justfile`, CI workflows).
   Run lint and test commands only if they are quick and have no side effects. Never run deploy, release or destructive commands.

3. **Re-verify overdue files.**
   For each `CLAUDE.md` or architecture doc whose `Last verified` date is overdue, compare its claims with the code. For a large area, use an Explore subagent.
   Fix what is wrong, delete what no longer applies, and set `Last verified` to today.

4. **Settle stale threads.**
   For each thread that is active but not updated for weeks, or finished but not archived, ask the user to choose one of these: still active (then `/threads:pickup` and `/threads:handoff` refresh it), paused (set `state: paused`), or finished (`/threads:close`).

5. **Fix the ADR index** for each ADR missing from `docs/decisions/README.md`.
   Report duplicate ADR numbers to the user instead of renumbering, because other docs may cite them.

6. **Re-run** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" audit` and confirm the errors are gone.

7. **Commit** the doc fixes, by path, with the message `docs: audit fixes <date>`.
   Skip the commit only if the user asked not to commit these docs, or a merge or rebase is in progress.
   Do not push unless the user asks.

8. **Reply** with what was fixed, what needs the user's decision, and what is clean.
