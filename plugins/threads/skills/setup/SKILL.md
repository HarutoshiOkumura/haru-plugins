---
name: setup
description: Set up a repository for multi-month work with Claude Code. Adds a short root CLAUDE.md, area CLAUDE.md files, docs/architecture.md, docs/decisions/ for ADRs, docs/threads/ for workstreams, a pull request template, and the settings that turn the threads plugin on for teammates. Moves status and history out of an existing CLAUDE.md without losing any of it.
argument-hint: "[notes about the repo]"
disable-model-invocation: true
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" *), Bash(git status *), Bash(git log *), Bash(git remote *), Bash(git ls-files *), Bash(git shortlog *)
---

# Set up a repo for threads

Arguments: $ARGUMENTS

## Facts gathered when this skill loaded

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" context`

Templates are in `${CLAUDE_SKILL_DIR}/templates/`.

## What goes where

| Layer | File | Holds | Loaded |
|---|---|---|---|
| Root | `CLAUDE.md` | One-paragraph purpose, map of areas, commands, conventions, pointers. Under 150 lines. No status or history. | Every session |
| Area | `<area>/CLAUDE.md` | The area's quirks, fragile parts, owner, `Last verified` date | When Claude works in that folder |
| Cross-cutting rules | `.claude/rules/<topic>.md` with `paths:` | Rules for files spread across areas | When Claude works on matching files |
| Big picture | `docs/architecture.md` | Components, data flow, invariants | On demand |
| Decisions | `docs/decisions/NNNN-*.md` | ADRs: never edited, only superseded | On demand, via the index |
| Workstreams | `docs/threads/<slug>/` | SPEC, STATUS, LOG, notes | The branch's STATUS at session start; the rest on demand |

## Steps

1. **Check the repo.**
   It must be a git repository; if it is not, offer `git init` and stop until the user answers.
   If `docs/threads/` already exists, this is a re-run: only add what is missing, and run step 6.

2. **Survey.**
   Find out: what the project is; its languages and frameworks; its top-level areas; its install, build, test, lint and run commands (from `package.json`, `pyproject.toml`, `Makefile`, `justfile`, CI workflows and the README); and the docs that exist (`CLAUDE.md` files, `AGENTS.md`, `README.md`, `docs/`, `.claude/commands/`, `.claude/rules/`, `.claude/settings.json`, and status, plan, decision or handoff files).
   For a repo with more than a handful of folders, use an Explore subagent so the file dumps stay out of this context.

3. **Propose a plan and wait for approval.** It lists:
   - each file to create;
   - existing content to move. Status, progress and history move out of `CLAUDE.md` into a thread's STATUS.md and LOG.md. Stable facts stay in the root file, or move to an area file or `docs/architecture.md`. Existing status, plan, decision and handoff files either become a thread (or ADRs) or stay where they are as reference, linked from the root file. Nothing is deleted: moved text lands verbatim in its new home, or in the thread's `notes.md`;
   - which areas get their own `CLAUDE.md`. Only areas with knowledge that is not obvious from the code get one (fragile parts, conventions, an owner); there is no empty boilerplate;
   - which threads to start for work already in flight, if any.

4. **Write the files.**
   - Root `CLAUDE.md` from `templates/root-CLAUDE.md`, under 150 lines, with real commands that were checked to exist. If the repo has `AGENTS.md` for other coding agents, keep the shared content in one file and import it with an `@AGENTS.md` line instead of copying it.
   - Area files from `templates/area-CLAUDE.md`, with `Last verified` set to today. Suggest an owner from `git shortlog -sn -- <area>` and confirm it with the user.
   - `docs/architecture.md` from `templates/architecture.md`, drafted from the survey, with `Last verified` set to today.
   - `docs/decisions/README.md` from `templates/decisions-README.md`. Turn an existing decision log into ADRs only if the user agrees; otherwise link to it.
   - `docs/threads/README.md` from `templates/threads-README.md`, plus the threads agreed in step 3, made by following `/threads:new` steps 5 and 6 (templates in `${CLAUDE_PLUGIN_ROOT}/skills/new/templates/`).
   - `.claude/settings.json`: merge these keys into the file, keeping everything already in it, so teammates who trust the folder get the plugin:

     ```json
     {
       "extraKnownMarketplaces": {
         "haru-plugins": { "source": { "source": "github", "repo": "HarutoshiOkumura/haru-plugins" } }
       },
       "enabledPlugins": { "threads@haru-plugins": true }
     }
     ```

   - `.gitignore`: add whichever of `.claude/worktrees/`, `.claude/settings.local.json` and `CLAUDE.local.md` are missing.
   - If the remote is on GitHub: `.github/pull_request_template.md` from `templates/pull_request_template.md`, merged into any existing template.

5. **Leave the rest alone.**
   Keep existing `.claude/commands/`, `.claude/rules/` and `.claude/agents/` files.
   Rules without `paths:` frontmatter load in every session; mention any that are large.

6. **Verify.**
   - Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/threads.py" audit` and fix every ERROR.
   - Check that the root `CLAUDE.md` is under 150 lines.
   - Run the quick lint and test commands from the root `CLAUDE.md` to confirm they work. Report failures; do not fix unrelated code during setup unless the user asks.

7. **Commit** the created and changed files, by path, with the message `docs: set up project memory for Claude Code`.
   Skip the commit only if the user asked not to commit these docs, or a merge or rebase is in progress.
   Do not push unless the user asks.

8. **Reply** with what was created, what moved where, the first thread to start (`/threads:new <slug>`), and what each teammate does once: trust the folder when Claude Code asks, then run `claude plugin install threads@haru-plugins`.
