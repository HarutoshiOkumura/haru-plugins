# Rollout: notes

Scratch space: findings, research, measurements, links.
Not loaded at session start; STATUS.md points here when a note matters for the next step.

## End-to-end test recipe

Unit tests cannot show what Claude does with a skill, so behaviour changes get a headless run against a scratch repo.

1. Make a scratch git repo with a root `CLAUDE.md`, a little code, and a thread in `docs/threads/<slug>/` (SPEC, STATUS with frontmatter, LOG).
2. Switch to a branch named `<slug>/<topic>` to test thread loading, or stay on `main` to test the thread list.
3. Run a session with the working copy of the plugin:

   ```sh
   claude -p --plugin-dir <this repo>/plugins/threads --model sonnet --max-turns 12 -- "/threads:pickup"
   ```

4. For a handoff, do some work first, then continue the same session:

   ```sh
   claude -p --continue --plugin-dir <this repo>/plugins/threads --model sonnet --max-turns 20 \
     --permission-mode acceptEdits --allowedTools "Bash(git add *)" "Bash(git commit *)" -- "/threads:handoff"
   ```

5. Check the result on disk (`git log --stat`, the thread files), not only Claude's reply.
6. To see what a skill was given, search the session transcript in `~/.claude/projects/<encoded scratch path>/<session id>.jsonl` for lines such as `today:` or `branch_thread:` from `threads.py context`.
7. `claude -p --continue ... -- "/compact"` exercises the PreCompact and post-compaction hooks.
