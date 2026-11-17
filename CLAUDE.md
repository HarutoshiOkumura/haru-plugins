# haru-plugins

A Claude Code plugin marketplace with one plugin, `threads`.
It gives repos a layered project memory (CLAUDE.md files, ADRs, thread docs), skills that keep it current, and hooks that load the right part at session start and after compaction.
People install it from GitHub; this repo is also where it is developed, using its own workflow.

## Map

| Area | Path | What it is |
|---|---|---|
| Marketplace | `.claude-plugin/marketplace.json` | Lists the plugins |
| Manifest | `plugins/threads/.claude-plugin/plugin.json` | Name, version, license |
| Hooks | `plugins/threads/hooks/hooks.json` | SessionStart and PreCompact; both call the script |
| Script | `plugins/threads/scripts/threads.py` | Hook output, facts for skills (`context`), docs audit |
| Skills | `plugins/threads/skills/` | One folder per slash command, with its templates |
| Docs | `README.md`, `plugins/threads/README.md` | Getting started; full reference and design notes |
| Tests | `tests/test_threads.py` | unittest against temporary git repos |
| CI | `.github/workflows/ci.yml` | Lint and tests on Linux; tests on macOS's own python3 |

## Commands

```sh
python3 -m unittest discover -s tests                 # tests
uvx ruff check . && uvx ruff format --check .         # lint and format
claude plugin validate . && claude plugin validate plugins/threads
python3 plugins/threads/scripts/threads.py audit      # this repo's own docs
claude --plugin-dir plugins/threads                   # one session with the working copy
```

## Conventions

- `threads.py` uses only the Python standard library and runs on Python 3.8 or newer, because hooks run on whatever `python3` a user has (macOS ships 3.9).
- The hooks and the `context` command exit 0 on any error and keep output under 9,000 characters (Claude Code caps hook output at 10,000). A broken hook must never block a session.
- Skills get dates, branches, thread names and ADR numbers from `threads.py context` through `!` injection, never from the model's guess.
- Skills commit only the doc files they touched, by path, as their own commit, and never push.
- Every skill is listed in the help card (`plugins/threads/skills/help/SKILL.md`), both READMEs and `plugins/threads/skills/setup/templates/threads-README.md`. `SkillDocsTest` fails otherwise.
- No file under `plugins/` is named `CLAUDE.md`: Claude Code would load it as instructions while working in this repo. Templates use names like `root-CLAUDE.md`.
- Test behaviour changes end to end, not only with unit tests: headless sessions against a scratch repo (recipe in `docs/threads/rollout/notes.md`).
- Markdown: one sentence per line, and plain dashes instead of em dashes.
- To release, raise `version` in `plugins/threads/.claude-plugin/plugin.json`; installs from GitHub only update when it changes.

## Project memory

- `docs/threads/<slug>/`: workstreams (SPEC, STATUS, LOG, notes). The session-start message names the branch's thread or lists the open ones.
- Design decisions so far are under "Design notes" in `plugins/threads/README.md`. New ones that constrain future work get an ADR with `/threads:adr`, which creates the decisions folder on first use.

## Working agreements

- One thread per session. Load it with `/threads:pickup <slug>`, or work on a branch named `<slug>/<topic>`.
- Run `/threads:handoff` before ending a session, `/clear` or `/compact`.
- When a change makes one of these docs wrong, fix the doc in the same change.
- Use a subagent for wide searches so file dumps stay out of the main context.
