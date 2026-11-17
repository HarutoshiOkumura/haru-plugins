"""Tests for plugins/threads/scripts/threads.py. Run: python3 -m unittest discover -s tests"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/threads/scripts/threads.py"
spec = importlib.util.spec_from_file_location("threads", SCRIPT)
threads = importlib.util.module_from_spec(spec)
sys.modules["threads"] = threads
spec.loader.exec_module(threads)

TODAY = dt.date(2026, 11, 17)


def setUpModule() -> None:
    # Keep the developer's git config (signing, hooks, templates) out of the test repos.
    global _config_dir
    _config_dir = tempfile.TemporaryDirectory()
    config = Path(_config_dir.name) / "gitconfig"
    config.write_text("[user]\n\tname = Test Author\n\temail = test@example.com\n")
    patcher = mock.patch.dict(
        os.environ,
        {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"},
    )
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
    unittest.addModuleCleanup(_config_dir.cleanup)


def status_md(
    slug: str, state: str = "active", updated: str = "2026-11-15", summary: str = "Doing it"
) -> str:
    return textwrap.dedent(
        f"""\
        ---
        thread: {slug}
        state: {state}
        summary: {summary}
        updated: {updated}
        ---

        # {slug}: status

        ## Next

        1. Do the first thing
        """
    )


class RepoTestCase(unittest.TestCase):
    """Each test gets a fresh git repo with one commit on main."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.git("init", "-q", "-b", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "init")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def add_thread(self, slug: str, **status: str) -> None:
        self.write(f"docs/threads/{slug}/STATUS.md", status_md(slug, **status))
        self.write(f"docs/threads/{slug}/SPEC.md", f"# {slug}\n")
        self.write(f"docs/threads/{slug}/LOG.md", f"# {slug}: log\n")


class FrontmatterTest(unittest.TestCase):
    def test_reads_flat_keys_and_keeps_colons_in_values(self) -> None:
        meta = threads.frontmatter("---\nstate: active\nsummary: a: b\n---\nbody")
        self.assertEqual(meta, {"state": "active", "summary": "a: b"})

    def test_strips_quotes(self) -> None:
        self.assertEqual(threads.frontmatter('---\nsummary: "x"\n---\n'), {"summary": "x"})

    def test_no_block_or_unterminated_block_gives_nothing(self) -> None:
        self.assertEqual(threads.frontmatter("# Title\nstate: active"), {})
        self.assertEqual(threads.frontmatter("---\nstate: active\n"), {})

    def test_ignores_nested_and_comment_lines(self) -> None:
        meta = threads.frontmatter("---\nstate: active\n  nested: x\n# c: d\n---\n")
        self.assertEqual(meta, {"state": "active"})


class BranchMatchTest(unittest.TestCase):
    slugs = frozenset({"auth-rewrite", "billing"})

    def test_matches(self) -> None:
        for branch in (
            "auth-rewrite",
            "auth-rewrite/token-refresh",
            "haru/auth-rewrite/x",
            "worktree-auth-rewrite",
        ):
            with self.subTest(branch=branch):
                self.assertEqual(threads.thread_for_branch(branch, self.slugs), "auth-rewrite")

    def test_does_not_match(self) -> None:
        for branch in (None, "", "main", "auth-rewrite-old", "feature/auth", "worktree-auth"):
            with self.subTest(branch=branch):
                self.assertIsNone(threads.thread_for_branch(branch, self.slugs))


class ClipTest(unittest.TestCase):
    def test_line_limit(self) -> None:
        self.assertEqual(threads.clip("a\nb\nc\n", 2, 100), ("a\nb", 1))

    def test_char_limit_cuts_whole_lines(self) -> None:
        self.assertEqual(threads.clip("aaaa\nbbbb\ncccc", 10, 10), ("aaaa\nbbbb", 1))

    def test_nothing_cut(self) -> None:
        self.assertEqual(threads.clip("a\nb", 10, 100), ("a\nb", 0))


class SessionStartTest(RepoTestCase):
    def test_silent_without_threads_dir(self) -> None:
        self.assertEqual(threads.session_start_text(self.root, "startup", TODAY), "")
        self.assertEqual(threads.pre_compact_text(self.root), "")

    def test_branch_thread_gets_its_status(self) -> None:
        self.add_thread("auth-rewrite")
        self.add_thread("billing")
        self.git("switch", "-q", "-c", "auth-rewrite/token-refresh")
        text = threads.session_start_text(self.root, "startup", TODAY)
        self.assertIn("# Thread: auth-rewrite", text)
        self.assertIn("1. Do the first thing", text)
        self.assertNotIn("billing", text)
        self.assertNotIn("compacted", text)

    def test_after_compaction_says_so(self) -> None:
        self.add_thread("auth-rewrite")
        self.git("switch", "-q", "-c", "auth-rewrite")
        text = threads.session_start_text(self.root, "compact", TODAY)
        self.assertIn("just compacted", text)

    def test_stale_status_is_flagged(self) -> None:
        self.add_thread("auth-rewrite", updated="2026-10-01")
        self.git("switch", "-q", "-c", "auth-rewrite")
        text = threads.session_start_text(self.root, "startup", TODAY)
        self.assertIn("last updated 47 days ago", text)

    def test_long_status_is_clipped_under_the_hook_cap(self) -> None:
        body = status_md("big") + "\n".join(f"- line {i} " + "x" * 90 for i in range(400))
        self.write("docs/threads/big/STATUS.md", body)
        self.git("switch", "-q", "-c", "big")
        text = threads.session_start_text(self.root, "startup", TODAY)
        self.assertLess(len(text), 10_000)
        self.assertIn("more lines not shown", text)

    def test_other_branch_lists_open_threads_active_first(self) -> None:
        self.add_thread("paused-one", state="paused", updated="2026-11-16")
        self.add_thread("old", updated="2026-11-01")
        self.add_thread("new", updated="2026-11-17")
        self.add_thread("finished", state="done")
        text = threads.session_start_text(self.root, "startup", TODAY)
        self.assertIn("No thread matches the branch `main`", text)
        order = [text.index(f"`{s}`") for s in ("new", "old", "paused-one")]
        self.assertEqual(order, sorted(order))
        self.assertIn("updated today", text)
        self.assertNotIn("finished", text)

    def test_archive_and_folders_without_status_are_ignored(self) -> None:
        self.write("docs/threads/_archive/gone/STATUS.md", status_md("gone"))
        self.write("docs/threads/draft/notes.md", "x")
        self.git("switch", "-q", "-c", "gone")
        text = threads.session_start_text(self.root, "startup", TODAY)
        self.assertIn("no thread is open", text)

    def test_detached_head_lists_threads(self) -> None:
        self.add_thread("auth-rewrite")
        self.git("checkout", "-q", "--detach")
        text = threads.session_start_text(self.root, "startup", TODAY)
        self.assertIn("Open threads", text)
        self.assertNotIn("No thread matches", text)

    def test_pre_compact_names_the_branch_thread(self) -> None:
        self.add_thread("auth-rewrite")
        self.git("switch", "-q", "-c", "auth-rewrite/x")
        text = threads.pre_compact_text(self.root)
        self.assertIn("thread, `auth-rewrite`", text)
        self.assertIn("Handoff pending", text)

    def test_pre_compact_lists_open_threads_off_branch(self) -> None:
        self.add_thread("auth-rewrite")
        self.assertIn("(`auth-rewrite`)", threads.pre_compact_text(self.root))


class HookEntryPointTest(RepoTestCase):
    def run_main(self, args: list[str], stdin: str) -> tuple[int, str]:
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out):
            code = threads.main(args)
        return code, out.getvalue()

    def test_reads_cwd_and_source_from_hook_input(self) -> None:
        self.add_thread("auth-rewrite")
        self.git("switch", "-q", "-c", "auth-rewrite")
        payload = json.dumps({"cwd": str(self.root / "docs"), "source": "compact"})
        code, out = self.run_main(["session-start"], payload)
        self.assertEqual(code, 0)
        self.assertIn("just compacted", out)

    def test_bad_input_never_fails(self) -> None:
        code, out = self.run_main(["--root", str(self.root), "session-start"], "not json")
        self.assertEqual((code, out), (0, ""))

    def test_errors_are_swallowed(self) -> None:
        err = io.StringIO()
        boom = mock.patch.object(threads, "session_start_text", side_effect=RuntimeError("boom"))
        with boom, redirect_stderr(err):
            code, out = self.run_main(["--root", str(self.root), "session-start"], "{}")
        self.assertEqual((code, out), (0, ""))
        self.assertIn("session-start failed: boom", err.getvalue())


class ContextTest(RepoTestCase):
    def test_reports_facts(self) -> None:
        self.add_thread("auth-rewrite")
        self.add_thread("finished", state="done")
        self.write("docs/threads/_archive/gone/STATUS.md", status_md("gone"))
        self.write("docs/decisions/0001-use-postgres.md", "# 1")
        self.write("docs/decisions/0007-use-redis.md", "# 7")
        self.git("switch", "-q", "-c", "auth-rewrite/x")
        text = threads.context_text(self.root, TODAY)
        self.assertIn("today: 2026-11-17", text)
        self.assertIn("author: Test Author", text)
        self.assertIn("branch: auth-rewrite/x", text)
        self.assertIn("branch_thread: auth-rewrite", text)
        self.assertIn("closed_but_not_archived:\n- `finished`", text)
        self.assertIn("archived_threads: gone", text)
        self.assertIn("2 ADRs in docs/decisions, next number 0008", text)
        self.assertIn("operation in progress: none", text)

    def test_unset_up_repo(self) -> None:
        text = threads.context_text(self.root, TODAY)
        self.assertIn("threads_dir: docs/threads (missing)", text)
        self.assertIn("open_threads: none", text)
        self.assertIn("decisions: docs/decisions missing", text)
        self.assertIn("git: 0 uncommitted changes", text)

    def test_not_a_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as plain:
            text = threads.context_text(Path(plain), TODAY)
        self.assertIn("branch: none", text)
        self.assertIn("git: not a git repository", text)


class ReferenceTest(RepoTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.write("app/main.py", "")
        self.write("services/billing/src/pay.py", "")

    def state(self, token: str, doc_dir: str = "") -> bool | None:
        return threads.reference_state(token, self.root / doc_dir, self.root)

    def test_existing_paths(self) -> None:
        self.assertTrue(self.state("app/main.py"))
        self.assertTrue(self.state("./app/"))
        self.assertTrue(self.state("src/pay.py", "services/billing"))
        self.assertTrue(self.state("../billing/src/pay.py", "services/billing"))

    def test_missing_path_under_a_real_folder(self) -> None:
        self.assertFalse(self.state("app/old.py"))
        self.assertFalse(self.state("src/old.py", "services/billing"))

    def test_not_repo_paths(self) -> None:
        self.assertIsNone(self.state("owner/repo"))
        self.assertIsNone(self.state("text/plain"))
        self.assertIsNone(self.state("../../outside/x.py"))

    def test_token_filter(self) -> None:
        line = (
            "See `app/main.py:12`, `docs/x.md#part`, `<slug>/STATUS.md`, `app/**`, "
            "`https://a.b/c`, `/abs/path`, `GET /find`, `~/x/y`, `uv run pytest`, `a/.../b`"
        )
        self.assertEqual(threads.path_tokens(line), ["app/main.py", "docs/x.md"])


class AuditTest(RepoTestCase):
    def audit(self) -> list[str]:
        return [f.render() for f in threads.audit(self.root, TODAY)]

    def test_clean_repo(self) -> None:
        self.write("CLAUDE.md", "# P\n\nSee `app/main.py`.\n")
        self.write("app/main.py", "")
        self.write("app/CLAUDE.md", "# App\n\nLast verified: 2026-11-01\n")
        self.write("docs/architecture.md", "# A\n\nLast verified: 2026-11-01\n")
        self.add_thread("auth-rewrite")
        self.write("docs/decisions/README.md", "| [0001](0001-x.md) |")
        self.write("docs/decisions/0001-x.md", "# 1")
        self.assertEqual(self.audit(), [])
        self.assertEqual(threads.audit_report([]), "No problems found.")

    def test_broken_reference_skips_code_fences(self) -> None:
        self.write("app/main.py", "")
        fenced = "```\napp/also_gone.py `app/x.py`\n```\n"
        self.write("CLAUDE.md", "# P\n\nUse `app/gone.py`.\n\n" + fenced)
        self.assertEqual(self.audit(), ["ERROR CLAUDE.md:3: `app/gone.py` does not exist"])

    def test_rules_are_checked(self) -> None:
        self.write("CLAUDE.md", "# P\n")
        self.write("app/main.py", "")
        self.write(".claude/rules/api.md", "---\npaths: app/**\n---\nSee `app/nope.py`.\n")
        self.assertIn("ERROR .claude/rules/api.md:4: `app/nope.py` does not exist", self.audit())

    def test_ignored_and_archived_claude_md_are_skipped(self) -> None:
        self.write("CLAUDE.md", "# P\n")
        self.write(".gitignore", "vendor/\n")
        self.write("vendor/lib/CLAUDE.md", "# no date\n")
        self.write("docs/threads/_archive/old/CLAUDE.md", "# no date\n")
        self.assertEqual(self.audit(), [])

    def test_root_and_area_files(self) -> None:
        self.write("CLAUDE.md", "x\n" * 151)
        self.write("a/CLAUDE.md", "# A\n")
        self.write("b/CLAUDE.md", "Last verified: 2026-01-01\n")
        self.write("c/CLAUDE.md", "Last verified: 2026-13-45\n")
        found = self.audit()
        self.assertIn("WARN  CLAUDE.md: 151 lines", found[0])
        self.assertIn("WARN  a/CLAUDE.md: no `Last verified: YYYY-MM-DD` line", found)
        self.assertIn("WARN  b/CLAUDE.md: last verified 320 days ago (2026-01-01)", found)
        self.assertIn("WARN  c/CLAUDE.md: `Last verified` date 2026-13-45 is not a date", found)

    def test_missing_root_claude_md(self) -> None:
        self.assertEqual(self.audit(), ["WARN  CLAUDE.md: the repo has no root CLAUDE.md"])

    def test_threads(self) -> None:
        self.write("CLAUDE.md", "# P\n")
        self.add_thread("stale", updated="2026-10-01")
        self.add_thread("finished", state="done")
        self.add_thread("odd", state="wip")
        self.write("docs/threads/bare/STATUS.md", "# no frontmatter\n")
        self.write("docs/threads/empty/notes.md", "")
        self.write("docs/threads/long/STATUS.md", status_md("long") + "x\n" * 80)
        self.write("docs/threads/long/SPEC.md", "")
        self.write("docs/threads/long/LOG.md", "")
        found = "\n".join(self.audit())
        self.assertIn("stale/STATUS.md: active but not updated for 47 days", found)
        self.assertIn("finished/STATUS.md: thread is done but not archived", found)
        self.assertIn("odd/STATUS.md: unknown state `wip`", found)
        self.assertIn("bare/STATUS.md: frontmatter is missing state, summary, updated", found)
        self.assertIn("docs/threads/empty: no STATUS.md", found)
        self.assertIn("docs/threads/empty: no SPEC.md", found)
        self.assertIn("long/STATUS.md: 92 lines", found)

    def test_decisions(self) -> None:
        self.write("CLAUDE.md", "# P\n")
        self.write("docs/decisions/README.md", "0001-a.md\n")
        self.write("docs/decisions/0001-a.md", "")
        self.write("docs/decisions/0002-b.md", "")
        self.write("docs/decisions/0002-c.md", "")
        found = self.audit()
        duplicate = "ERROR docs/decisions: ADR number 0002 is used by 0002-b.md, 0002-c.md"
        self.assertEqual(found[0], duplicate)
        self.assertIn("WARN  docs/decisions/README.md: 0002-b.md is not in the index", found)

    def test_strict_exit_code(self) -> None:
        self.write("app/main.py", "")
        self.write("CLAUDE.md", "`app/gone.py`\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(threads.main(["--root", str(self.root), "audit"]), 0)
            self.assertEqual(threads.main(["--root", str(self.root), "audit", "--strict"]), 1)


PLUGIN = SCRIPT.parents[1]


class SkillDocsTest(unittest.TestCase):
    """Every skill is documented wherever users look for it, so the docs cannot drift silently."""

    skills = sorted(p.name for p in (PLUGIN / "skills").iterdir() if (p / "SKILL.md").is_file())

    def test_skill_frontmatter(self) -> None:
        for name in self.skills:
            with self.subTest(skill=name):
                meta = threads.frontmatter((PLUGIN / "skills" / name / "SKILL.md").read_text())
                self.assertEqual(meta.get("name"), name)
                self.assertGreater(len(meta.get("description", "")), 40)

    def test_every_skill_is_documented(self) -> None:
        docs = {
            "help card": PLUGIN / "skills/help/SKILL.md",
            "plugin README": PLUGIN / "README.md",
            "root README": PLUGIN.parents[1] / "README.md",
            "docs/threads/README.md template": PLUGIN / "skills/setup/templates/threads-README.md",
        }
        for label, path in docs.items():
            text = path.read_text()
            for name in self.skills:
                with self.subTest(doc=label, skill=name):
                    self.assertTrue(
                        f"`/threads:{name}" in text, f"{label} does not mention /threads:{name}"
                    )

    def test_help_card_markers(self) -> None:
        text = (PLUGIN / "skills/help/SKILL.md").read_text()
        self.assertEqual(text.count("\nCARD START\n"), 1)
        self.assertEqual(text.count("\nCARD END\n"), 1)
        self.assertLess(text.index("CARD START\n"), text.index("CARD END\n"))


if __name__ == "__main__":
    unittest.main()
