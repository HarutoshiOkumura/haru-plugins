#!/usr/bin/env python3
"""Helper for the threads plugin: hooks, skill context, and the docs audit.

Usage:
  threads.py session-start     SessionStart hook: the branch's thread STATUS.md, or the list.
  threads.py pre-compact       PreCompact hook: instructions for the compaction summary.
  threads.py context           Facts for skills: date, author, branch, threads, ADRs, git state.
  threads.py audit [--strict]  Report stale or broken project docs. --strict exits 1 on errors.

Standard library only, Python 3.9+ (the python3 that ships with macOS).
The hook and context commands always exit 0, so a problem here never blocks a session or a skill.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections.abc import Container
from dataclasses import dataclass
from pathlib import Path

THREADS_DIR = Path("docs/threads")
DECISIONS_DIR = Path("docs/decisions")
ARCHITECTURE_DOC = Path("docs/architecture.md")
RULES_DIR = Path(".claude/rules")
ARCHIVE = "_archive"

HOOK_CHAR_BUDGET = 9000  # Claude Code caps hook output at 10,000 characters.
STATUS_LINES_SHOWN = 120
STATUS_LINE_LIMIT = 80
ROOT_CLAUDE_MD_LINE_LIMIT = 150
STALE_THREAD_DAYS = 21
STALE_VERIFIED_DAYS = 90
LISTED_THREADS = 20
SUMMARY_CHARS = 120

OPEN_STATES = ("active", "paused", "blocked")
CLOSED_STATES = ("done", "abandoned", "superseded")
REQUIRED_STATUS_KEYS = ("state", "summary", "updated")
# `claude -w <name>` creates the branch worktree-<name>.
WORKTREE_BRANCH_PREFIX = "worktree-"
GIT_OPERATIONS = {
    "rebase-merge": "rebase",
    "rebase-apply": "rebase",
    "MERGE_HEAD": "merge",
    "CHERRY_PICK_HEAD": "cherry-pick",
    "REVERT_HEAD": "revert",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERIFIED_RE = re.compile(r"^Last verified:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
ADR_RE = re.compile(r"^(\d{4})-.+\.md$")
CODE_SPAN_RE = re.compile(r"`([^`\s]+)`")
LINE_SUFFIX_RE = re.compile(r":\d+(-\d+)?$")
NOT_PATH_CHARS = frozenset("<>*?{}[]|:;=,()'\"$~@!\\")


# Git


def git(args: list[str], cwd: Path) -> str | None:
    """Run git and return its stripped stdout, or None if git is missing or the command fails."""
    try:
        done = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def repo_root(start: Path) -> Path:
    top = git(["rev-parse", "--show-toplevel"], start)
    return Path(top) if top else start


def current_branch(root: Path) -> str | None:
    """The checked-out branch, also before the first commit. None when HEAD is detached."""
    return git(["symbolic-ref", "--quiet", "--short", "HEAD"], root) or None


def git_operation(root: Path) -> str | None:
    """The merge, rebase, cherry-pick or revert in progress, if any."""
    for marker, name in GIT_OPERATIONS.items():
        path = git(["rev-parse", "--git-path", marker], root)
        if path and (root / path).exists():
            return name
    return None


# Thread docs


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def frontmatter(text: str) -> dict[str, str]:
    """Flat `key: value` pairs from a leading --- block. Nested YAML is not supported."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta
        key, sep, value = line.partition(":")
        if sep and key and not key[0].isspace() and not key.startswith("#"):
            meta[key.strip()] = value.strip().strip("\"'")
    return {}  # An unterminated block is not frontmatter.


def parse_date(value: str | None) -> dt.date | None:
    if not value or not DATE_RE.match(value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class Thread:
    slug: str
    folder: Path
    meta: dict[str, str]
    has_status: bool

    @property
    def state(self) -> str:
        return (self.meta.get("state") or "unknown").lower()

    @property
    def summary(self) -> str:
        return self.meta.get("summary", "")

    @property
    def updated(self) -> dt.date | None:
        return parse_date(self.meta.get("updated"))

    @property
    def is_open(self) -> bool:
        return self.state not in CLOSED_STATES

    def age_days(self, today: dt.date) -> int | None:
        return (today - self.updated).days if self.updated else None


def load_threads(root: Path) -> list[Thread]:
    """Every thread folder in docs/threads/, excluding _archive/ and dot folders."""
    base = root / THREADS_DIR
    if not base.is_dir():
        return []
    threads = []
    for folder in sorted(base.iterdir()):
        if not folder.is_dir() or folder.name.startswith(("_", ".")):
            continue
        status = folder / "STATUS.md"
        meta = frontmatter(read_text(status)) if status.is_file() else {}
        threads.append(Thread(folder.name, folder, meta, status.is_file()))
    return threads


def archived_slugs(root: Path) -> list[str]:
    base = root / THREADS_DIR / ARCHIVE
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir())


def thread_for_branch(branch: str | None, slugs: Container[str]) -> str | None:
    """Map a branch to a thread slug.

    A branch belongs to a thread when one of its /-separated segments is the slug,
    optionally with the worktree- prefix that `claude -w` adds:
    `auth-rewrite`, `auth-rewrite/token-refresh`, `haru/auth-rewrite/x`, `worktree-auth-rewrite`.
    """
    if not branch:
        return None
    for segment in branch.split("/"):
        candidates = [segment]
        if segment.startswith(WORKTREE_BRANCH_PREFIX):
            candidates.append(segment[len(WORKTREE_BRANCH_PREFIX) :])
        for candidate in candidates:
            if candidate in slugs:
                return candidate
    return None


def sort_for_listing(threads: list[Thread]) -> list[Thread]:
    """Active first, then paused and blocked; newest update first within each state."""
    rank = {state: i for i, state in enumerate(OPEN_STATES)}
    return sorted(
        threads,
        key=lambda t: (rank.get(t.state, len(rank)), -(t.updated or dt.date.min).toordinal()),
    )


def describe(thread: Thread, today: dt.date) -> str:
    age = thread.age_days(today)
    if age is None:
        when = "no update date"
    elif age == 0:
        when = "updated today"
    else:
        when = f"updated {thread.updated.isoformat()}, {age} days ago"
    summary = thread.summary or "(no summary)"
    if len(summary) > SUMMARY_CHARS:
        summary = summary[: SUMMARY_CHARS - 3] + "..."
    return f"- `{thread.slug}` ({thread.state}, {when}): {summary}"


def clip(text: str, max_lines: int, max_chars: int) -> tuple[str, int]:
    """Cut text to whole lines within both limits. Returns the text and how many lines were cut."""
    lines = text.rstrip("\n").splitlines()
    kept: list[str] = []
    used = 0
    for line in lines[:max_lines]:
        if used + len(line) + 1 > max_chars:
            break
        kept.append(line)
        used += len(line) + 1
    return "\n".join(kept), len(lines) - len(kept)


# Hook and context output


def session_start_text(root: Path, source: str, today: dt.date) -> str:
    if not (root / THREADS_DIR).is_dir():
        return ""  # This repo does not use thread docs. Stay silent.
    threads = [t for t in load_threads(root) if t.has_status]
    branch = current_branch(root)
    slug = thread_for_branch(branch, {t.slug for t in threads})
    if slug:
        thread = next(t for t in threads if t.slug == slug)
        return thread_brief(root, thread, branch or "", source, today)
    return thread_index(threads, branch, today)


def thread_brief(root: Path, thread: Thread, branch: str, source: str, today: dt.date) -> str:
    rel = thread.folder.relative_to(root).as_posix()
    header = [
        f"# Thread: {thread.slug}",
        f"This session is on branch `{branch}`, which belongs to the thread `{thread.slug}`.",
        f"Its STATUS.md follows. SPEC.md (goal, scope, done criteria), LOG.md (history, newest "
        f"first) and notes.md are in `{rel}/`; read them when the task needs them.",
        "Run /threads:handoff before the session ends, so the next session can continue.",
    ]
    if source == "compact":
        header.append(
            "The conversation was just compacted. Work done since the last handoff is in the "
            "summary, not yet in these files."
        )
    age = thread.age_days(today)
    if age is not None and age > STALE_THREAD_DAYS:
        header.append(
            f"STATUS.md was last updated {age} days ago. Check `git log` for later work "
            "before relying on it."
        )
    head = "\n".join(header)
    budget = HOOK_CHAR_BUDGET - len(head) - 200
    status, cut = clip(read_text(thread.folder / "STATUS.md"), STATUS_LINES_SHOWN, budget)
    parts = [head, "", f"--- {rel}/STATUS.md ---", status]
    if cut:
        parts.append(
            f"[{cut} more lines not shown. STATUS.md is over its size budget; "
            "trim it at the next handoff.]"
        )
    return "\n".join(parts)


def thread_index(threads: list[Thread], branch: str | None, today: dt.date) -> str:
    open_threads = sort_for_listing([t for t in threads if t.is_open])
    if not open_threads:
        return (
            "# Threads\nThis repo keeps long-running work in `docs/threads/`, and no thread "
            "is open. /threads:new <slug> starts one."
        )
    on_branch = f"No thread matches the branch `{branch}`. " if branch else ""
    lines = [
        "# Threads",
        f"This repo keeps long-running work in `docs/threads/`. {on_branch}Open threads:",
    ]
    lines += [describe(t, today) for t in open_threads[:LISTED_THREADS]]
    if len(open_threads) > LISTED_THREADS:
        lines.append(f"- ...and {len(open_threads) - LISTED_THREADS} more in `docs/threads/`.")
    lines += [
        "If the request belongs to one of these, load it with /threads:pickup <slug> before "
        "starting, and run /threads:handoff before the session ends.",
        "Branches named `<slug>/<topic>`, and worktrees made with `claude -w <slug>`, load "
        "their thread automatically.",
    ]
    return "\n".join(lines)


def pre_compact_text(root: Path) -> str:
    if not (root / THREADS_DIR).is_dir():
        return ""
    threads = [t for t in load_threads(root) if t.has_status]
    slug = thread_for_branch(current_branch(root), {t.slug for t in threads})
    lines = ["This repo keeps long-running work in thread docs (`docs/threads/`). In the summary:"]
    if slug:
        lines.append(
            f"- Name the session's thread, `{slug}`. Its STATUS.md is loaded again after "
            "compaction, so do not repeat what it already says."
        )
    else:
        names = ", ".join(f"`{t.slug}`" for t in threads if t.is_open) or "none open"
        lines.append(f"- If the session worked on a thread ({names}), name it.")
    lines += [
        "- Keep everything not yet written in the thread's STATUS.md or LOG.md: files and "
        "commits changed, decisions and their reasons, approaches that failed and why, failing "
        "test names and exact error messages, measured numbers, and the next concrete step.",
        "- Say whether /threads:handoff ran after the last change. If it did not, end the "
        "summary with: Handoff pending: run /threads:handoff.",
    ]
    return "\n".join(lines)


def next_adr_number(root: Path) -> tuple[int, str]:
    folder = root / DECISIONS_DIR
    numbers = [
        int(m.group(1))
        for p in (folder.iterdir() if folder.is_dir() else [])
        if (m := ADR_RE.match(p.name))
    ]
    return len(numbers), f"{max(numbers, default=0) + 1:04d}"


def context_text(root: Path, today: dt.date) -> str:
    branch = current_branch(root)
    threads = load_threads(root)
    slug = thread_for_branch(branch, {t.slug for t in threads if t.has_status})
    has_threads_dir = (root / THREADS_DIR).is_dir()
    lines = [
        f"today: {today.isoformat()}",
        f"author: {git(['config', 'user.name'], root) or 'unknown'}",
        f"repo_root: {root}",
        f"branch: {branch or 'none (detached HEAD or not a git repo)'}",
        f"branch_thread: {slug or 'none'}",
        f"threads_dir: docs/threads ({'present' if has_threads_dir else 'missing'})",
    ]
    open_threads = sort_for_listing([t for t in threads if t.is_open])
    closed = [t for t in threads if not t.is_open]
    lines.append("open_threads:" + ("" if open_threads else " none"))
    lines += [describe(t, today) for t in open_threads]
    if closed:
        lines.append("closed_but_not_archived:")
        lines += [describe(t, today) for t in closed]
    archived = archived_slugs(root)
    lines.append(f"archived_threads: {', '.join(archived) if archived else 'none'}")
    if (root / DECISIONS_DIR).is_dir():
        count, number = next_adr_number(root)
        lines.append(f"decisions: {count} ADRs in docs/decisions, next number {number}")
    else:
        lines.append("decisions: docs/decisions missing")
    status = git(["status", "--porcelain"], root)
    if status is None:
        lines.append("git: not a git repository")
    else:
        changed = len(status.splitlines()) if status else 0
        lines.append(
            f"git: {changed} uncommitted changes; operation in progress: "
            f"{git_operation(root) or 'none'}"
        )
    return "\n".join(lines)


# Audit


@dataclass
class Finding:
    level: str  # ERROR or WARN
    path: str
    message: str
    line: int | None = None

    def render(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{self.level:<5} {where}: {self.message}"


def tracked_files(root: Path, name: str) -> list[Path]:
    """Files called `name` that git tracks or would track. Falls back to a walk outside git."""
    listing = git(["ls-files", "--cached", "--others", "--exclude-standard", "-z"], root)
    if listing is not None:
        paths = {root / p for p in listing.split("\0") if p and Path(p).name == name}
    else:
        skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "worktrees"}
        paths = set()
        for folder, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip]
            if name in files:
                paths.add(Path(folder) / name)
    archive = root / THREADS_DIR / ARCHIVE
    return sorted(p for p in paths if p.is_file() and archive not in p.parents)


def path_tokens(line: str) -> list[str]:
    """Code spans in a line that look like relative file paths."""
    tokens = []
    for match in CODE_SPAN_RE.finditer(line):
        token = LINE_SUFFIX_RE.sub("", match.group(1).split("#", 1)[0])
        if "/" not in token or token.startswith("/") or "..." in token:
            continue
        if any(c in NOT_PATH_CHARS for c in token):
            continue
        tokens.append(token)
    return tokens


def within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def reference_state(token: str, doc_dir: Path, root: Path) -> bool | None:
    """True if the path exists, False if it looks like a repo path but is missing.

    None when it is not a repo path, for example `owner/repo` or a path outside the repo.
    A missing path counts as a repo path when its first segment exists, relative to the
    document's folder or the repo root.
    """
    rel = token.rstrip("/")
    parts = [p for p in Path(rel).parts if p != "."]
    if not parts:
        return None
    lead = 0
    while lead < len(parts) and parts[lead] == "..":
        lead += 1
    anchor_parts = parts[: lead + 1]
    looks_like_repo_path = False
    for base in (doc_dir, root):
        target = Path(os.path.normpath(base.joinpath(*parts)))
        if not within(target, root):
            continue
        if target.exists():
            return True
        anchor = Path(os.path.normpath(base.joinpath(*anchor_parts)))
        if anchor != root and within(anchor, root) and anchor.exists():
            looks_like_repo_path = True
    return False if looks_like_repo_path else None


def check_references(doc: Path, root: Path) -> list[Finding]:
    findings = []
    in_fence = False
    for number, line in enumerate(read_text(doc).splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for token in path_tokens(line):
            if reference_state(token, doc.parent, root) is False:
                findings.append(
                    Finding(
                        "ERROR",
                        doc.relative_to(root).as_posix(),
                        f"`{token}` does not exist",
                        number,
                    )
                )
    return findings


def check_verified(doc: Path, root: Path, today: dt.date) -> list[Finding]:
    rel = doc.relative_to(root).as_posix()
    match = VERIFIED_RE.search(read_text(doc))
    if not match:
        return [Finding("WARN", rel, "no `Last verified: YYYY-MM-DD` line")]
    verified = parse_date(match.group(1))
    if verified is None:
        return [Finding("WARN", rel, f"`Last verified` date {match.group(1)} is not a date")]
    age = (today - verified).days
    if age > STALE_VERIFIED_DAYS:
        return [Finding("WARN", rel, f"last verified {age} days ago ({verified.isoformat()})")]
    return []


def check_claude_md(root: Path, today: dt.date) -> list[Finding]:
    findings = []
    docs = tracked_files(root, "CLAUDE.md")
    root_docs = {root / "CLAUDE.md", root / ".claude" / "CLAUDE.md"}
    if not any(d in root_docs for d in docs):
        findings.append(Finding("WARN", "CLAUDE.md", "the repo has no root CLAUDE.md"))
    for doc in docs:
        rel = doc.relative_to(root).as_posix()
        if doc in root_docs:
            length = len(read_text(doc).splitlines())
            if length > ROOT_CLAUDE_MD_LINE_LIMIT:
                findings.append(
                    Finding(
                        "WARN",
                        rel,
                        f"{length} lines; keep the root CLAUDE.md under "
                        f"{ROOT_CLAUDE_MD_LINE_LIMIT} and move detail to area files or docs/",
                    )
                )
        else:
            findings += check_verified(doc, root, today)
        findings += check_references(doc, root)
    rules = root / RULES_DIR
    for rule in sorted(rules.glob("**/*.md")) if rules.is_dir() else []:
        findings += check_references(rule, root)
    architecture = root / ARCHITECTURE_DOC
    if architecture.is_file():
        findings += check_verified(architecture, root, today)
        findings += check_references(architecture, root)
    return findings


def check_threads(root: Path, today: dt.date) -> list[Finding]:
    findings = []
    for thread in load_threads(root):
        rel = thread.folder.relative_to(root).as_posix()
        for name in ("SPEC.md", "LOG.md"):
            if not (thread.folder / name).is_file():
                findings.append(Finding("WARN", rel, f"no {name}"))
        if not thread.has_status:
            findings.append(Finding("WARN", rel, "no STATUS.md"))
            continue
        status_rel = f"{rel}/STATUS.md"
        missing = [k for k in REQUIRED_STATUS_KEYS if not thread.meta.get(k)]
        if missing:
            findings.append(
                Finding("WARN", status_rel, f"frontmatter is missing {', '.join(missing)}")
            )
        if thread.meta.get("updated") and thread.updated is None:
            findings.append(Finding("WARN", status_rel, "`updated` is not a YYYY-MM-DD date"))
        if thread.meta.get("state") and thread.state not in OPEN_STATES + CLOSED_STATES:
            findings.append(
                Finding(
                    "WARN",
                    status_rel,
                    f"unknown state `{thread.state}`; use one of "
                    f"{', '.join(OPEN_STATES + CLOSED_STATES)}",
                )
            )
        if thread.state in CLOSED_STATES:
            findings.append(
                Finding(
                    "WARN",
                    status_rel,
                    f"thread is {thread.state} but not archived; run /threads:close {thread.slug}",
                )
            )
        age = thread.age_days(today)
        if thread.state == "active" and age is not None and age > STALE_THREAD_DAYS:
            findings.append(
                Finding(
                    "WARN",
                    status_rel,
                    f"active but not updated for {age} days; hand off, pause or close it",
                )
            )
        length = len(read_text(thread.folder / "STATUS.md").splitlines())
        if length > STATUS_LINE_LIMIT:
            findings.append(
                Finding(
                    "WARN",
                    status_rel,
                    f"{length} lines; keep STATUS.md under {STATUS_LINE_LIMIT} "
                    "(history belongs in LOG.md, detail in notes.md)",
                )
            )
    return findings


def check_decisions(root: Path) -> list[Finding]:
    folder = root / DECISIONS_DIR
    if not folder.is_dir():
        return []
    findings = []
    by_number: dict[str, list[str]] = {}
    for path in sorted(folder.glob("*.md")):
        match = ADR_RE.match(path.name)
        if match:
            by_number.setdefault(match.group(1), []).append(path.name)
    rel = DECISIONS_DIR.as_posix()
    for number, names in sorted(by_number.items()):
        if len(names) > 1:
            findings.append(
                Finding("ERROR", rel, f"ADR number {number} is used by {', '.join(names)}")
            )
    index = folder / "README.md"
    if not index.is_file():
        if by_number:
            findings.append(Finding("WARN", rel, "no README.md index"))
        return findings
    index_text = read_text(index)
    for names in by_number.values():
        for name in names:
            if name not in index_text:
                findings.append(Finding("WARN", f"{rel}/README.md", f"{name} is not in the index"))
    return findings


def audit(root: Path, today: dt.date) -> list[Finding]:
    return check_claude_md(root, today) + check_threads(root, today) + check_decisions(root)


def audit_report(findings: list[Finding]) -> str:
    if not findings:
        return "No problems found."
    ordered = sorted(findings, key=lambda f: (f.level != "ERROR", f.path, f.line or 0))
    errors = sum(f.level == "ERROR" for f in findings)
    warnings = len(findings) - errors
    lines = [f.render() for f in ordered]
    lines.append(f"{errors} errors, {warnings} warnings")
    return "\n".join(lines)


# Entry point


def hook_root() -> tuple[Path, str]:
    """Where the session runs and why the hook fired, from the hook's stdin JSON."""
    payload = {}
    if not sys.stdin.isatty():
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except (ValueError, OSError):
            payload = {}
    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return repo_root(Path(cwd)), str(payload.get("source") or "")


def emit(text: str) -> None:
    if text:
        sys.stdout.write(text + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", help="repository root (default: from the hook input or cwd)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("session-start", help="SessionStart hook")
    sub.add_parser("pre-compact", help="PreCompact hook")
    sub.add_parser("context", help="facts for skills")
    audit_parser = sub.add_parser("audit", help="report stale or broken project docs")
    audit_parser.add_argument("--strict", action="store_true", help="exit 1 when there are errors")
    args = parser.parse_args(argv)
    today = dt.date.today()

    if args.command == "audit":
        root = repo_root(Path(args.root or os.getcwd()))
        findings = audit(root, today)
        emit(audit_report(findings))
        return 1 if args.strict and any(f.level == "ERROR" for f in findings) else 0

    # Hooks and skill context must never fail the session or the skill that runs them.
    try:
        if args.command == "context":
            emit(context_text(repo_root(Path(args.root or os.getcwd())), today))
            return 0
        root, source = hook_root()
        if args.root:
            root = repo_root(Path(args.root))
        if args.command == "session-start":
            emit(session_start_text(root, source, today))
        else:
            emit(pre_compact_text(root))
    except Exception as error:  # noqa: BLE001 - report and carry on
        sys.stderr.write(f"threads plugin: {args.command} failed: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
