---
name: adr
description: Record an architecture decision record (ADR) in docs/decisions/ for a choice that crosses threads or areas, or that someone might later reverse without knowing why. Use when a decision about technology, data shapes, interfaces, conventions or trade-offs is made that other work must follow, or when the user asks to record a decision.
argument-hint: "<short title> [supersedes NNNN]"
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" *), Bash(git status *), Bash(git log *)
---

# Record a decision

Arguments: $ARGUMENTS

## Facts gathered when this skill loaded

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" context`

## Steps

1. **Name the file.**
   If `docs/decisions/` is missing, create it with the index from `${CLAUDE_PLUGIN_ROOT}/skills/setup/templates/decisions-README.md`.
   The number is the `next number` from the facts.
   The file is `docs/decisions/<NNNN>-<kebab-case-title>.md`.

2. **Write it** from `${CLAUDE_SKILL_DIR}/template.md`, using what the conversation established.
   - Context: the forces and constraints that made a decision necessary.
   - Decision: what we will do, in one short paragraph.
   - Consequences: what gets easier, what gets harder, what must now be done.
   - Alternatives considered: each one, and why it was not chosen.

   Ask the user only for what the conversation does not settle.
   Status is `Accepted` unless the user says `Proposed`.
   Thread is the current thread's slug, or `none`.

3. **Supersede, if this replaces an earlier decision.**
   In the old ADR, change only its Status line, to `Superseded by [<NNNN>](<new file name>)`.
   Accepted ADRs are otherwise never edited; a changed decision gets a new ADR.

4. **Update the index** in `docs/decisions/README.md`: add a row, and update the status of any superseded row.

5. **Link it.**
   Add it to the current thread's SPEC.md "Related" section.
   If the decision constrains an area, add one line to that area's `CLAUDE.md`: `See ADR <NNNN>: <title>.`

6. **Commit** the new ADR and the files edited in steps 3 to 5, by path, with the message `docs: ADR <NNNN> <title>`.
   Skip the commit only if the user asked not to commit these docs, or a merge or rebase is in progress.
   Do not push unless the user asks.
