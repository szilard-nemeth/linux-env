#!/usr/bin/env python3
"""
Commit and push exported Claude sessions (claude-sessions/) in knowledge-base-private.

Only commits when the local branch is fully pushed: if it has commits that
origin/<branch> lacks, the script stops and changes nothing, so the session
export never gets mixed in with unpushed work. If the branch is only behind, it
is fast-forwarded first so that the push afterwards succeeds.

Only paths under claude-sessions/ are committed. Anything else that is staged
or modified in the repo is left as it is.
"""

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

KB_PRIVATE_ROOT = Path(os.environ.get("KB_PRIVATE_REPO", "~/development/my-repos/knowledge-base-private")).expanduser()
SESSIONS_SUBDIR = "claude-sessions"
BRANCH = "master"
REMOTE = "origin"
COMMIT_SUBJECT = "Export Claude session markdown files"


class PreconditionError(Exception):
    pass


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    if result.returncode != 0:
        raise PreconditionError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.rstrip("\n")


def ahead_behind(repo: Path, branch: str, upstream: str) -> Tuple[int, int]:
    out = git(repo, "rev-list", "--left-right", "--count", f"{branch}...{upstream}")
    ahead, behind = (int(n) for n in out.split())
    return ahead, behind


def changed_session_files(repo: Path, subdir: str) -> List[str]:
    # --untracked-files=all lists new files one by one instead of collapsing them into their new directory
    out = git(repo, "status", "--porcelain", "--untracked-files=all", "--", subdir)
    return [line for line in out.splitlines() if line.strip()]


def build_commit_message(changes: List[str], today: datetime.date) -> str:
    added = sum(1 for c in changes if c.startswith("??") or c[0] == "A")
    deleted = sum(1 for c in changes if "D" in c[:2])
    modified = len(changes) - added - deleted
    return f"{COMMIT_SUBJECT} ({today.isoformat()})\n\n{added} added, {modified} modified, {deleted} deleted"


def commit_claude_sessions(
    repo: Path = KB_PRIVATE_ROOT,
    subdir: str = SESSIONS_SUBDIR,
    branch: str = BRANCH,
    remote: str = REMOTE,
    push: bool = True,
    dry_run: bool = False,
) -> bool:
    """Returns True if a commit was made (or would be made, with dry_run)."""
    upstream = f"{remote}/{branch}"

    current = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if current != branch:
        raise PreconditionError(f"{repo} is on branch '{current}', expected '{branch}'")

    git(repo, "fetch", "--quiet", remote, branch)
    ahead, behind = ahead_behind(repo, branch, upstream)
    if ahead:
        raise PreconditionError(
            f"{branch} has {ahead} commit(s) not pushed to {upstream} (and is behind by {behind}). "
            f"Push or reconcile them first, then re-run."
        )

    if behind:
        if dry_run:
            print(f"DRY-RUN: would fast-forward {branch} by {behind} commit(s) from {upstream}")
        else:
            print(f"Fast-forwarding {branch} by {behind} commit(s) from {upstream}")
            # Refuses (and leaves everything untouched) if it would overwrite local modifications
            git(repo, "merge", "--ff-only", "--quiet", upstream)

    changes = changed_session_files(repo, subdir)
    if not changes:
        print(f"Nothing to commit under {subdir}/")
        return False

    message = build_commit_message(changes, datetime.date.today())
    if dry_run:
        print(f"DRY-RUN: would commit {len(changes)} file(s) under {subdir}/:")
        print("\n".join(f"  {c}" for c in changes))
        print(f"DRY-RUN: commit message:\n{message}")
        return True

    git(repo, "add", "-A", "--", subdir)
    # With a pathspec, only these paths go into the commit, even if other files are staged
    git(repo, "commit", "--quiet", "-m", message, "--", subdir)
    print(f"Committed {len(changes)} file(s): {git(repo, 'log', '-1', '--oneline')}")

    if push:
        git(repo, "push", "--quiet", remote, branch)
        print(f"Pushed to {upstream}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=KB_PRIVATE_ROOT, help="knowledge-base-private checkout")
    parser.add_argument("--no-push", action="store_true", help="commit only, do not push")
    parser.add_argument("--dry-run", action="store_true", help="show what would be committed, change nothing")
    args = parser.parse_args()

    try:
        commit_claude_sessions(repo=args.repo.expanduser(), push=not args.no_push, dry_run=args.dry_run)
    except PreconditionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
