# {Project name}

{One paragraph: what this is, who uses it, and what matters most here (for example correctness over speed).}

## Map

| Area | Path | What it is |
|---|---|---|
| {Area} | `{path}/` | {One line} |

Areas with their own `CLAUDE.md` load it when you work in them.

## Commands

```sh
{install}
{build}
{test}        # one test: {how}
{lint}
{run}
```

## Conventions

- {A convention that is not obvious from the code}

## Project memory

- `docs/architecture.md`: the big picture. Read it before changes that cross areas.
- `docs/decisions/`: ADRs, indexed in its `README.md`. Follow accepted ones. A changed decision gets a new ADR that supersedes the old one; accepted ADRs are not edited.
- `docs/threads/<slug>/`: long-running workstreams (SPEC, STATUS, LOG, notes). The session-start message names the branch's thread or lists the open ones.
- `.claude/rules/`: rules that cut across areas, scoped by path.

## Working agreements

- One thread per session. Load it with `/threads:pickup <slug>`. Branches named `<slug>/<topic>`, and worktrees made with `claude -w <slug>`, load it automatically.
- Run `/threads:handoff` before ending a session, `/clear` or `/compact`.
- A decision that affects other threads or areas gets an ADR (`/threads:adr`).
- Project knowledge goes in these files, where teammates' sessions see it, not in personal memory.
- When a change makes one of these docs wrong, fix the doc in the same change.
- Use a subagent for wide searches ("everything that touches X") so the file dumps stay out of the main context.
