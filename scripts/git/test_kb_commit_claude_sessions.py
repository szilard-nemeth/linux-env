#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from kb_commit_claude_sessions import PreconditionError, commit_claude_sessions  # noqa: E402


def run(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def make_clone(origin: Path, dest: Path) -> Path:
    run(origin.parent, "clone", "--quiet", str(origin), str(dest))
    run(dest, "config", "user.name", "Test")
    run(dest, "config", "user.email", "test@example.com")
    return dest


@pytest.fixture
def repos(tmp_path):
    """A bare origin, a local clone (the KB checkout) and a second clone acting as another machine."""
    origin = tmp_path / "origin.git"
    run(tmp_path, "init", "--quiet", "--bare", "--initial-branch=master", str(origin))
    local = make_clone(origin, tmp_path / "local")
    (local / "claude-sessions").mkdir()
    (local / "claude-sessions" / "old.md").write_text("old\n")
    (local / "notes.md").write_text("notes\n")
    run(local, "add", "-A")
    run(local, "commit", "--quiet", "-m", "init")
    run(local, "push", "--quiet", "origin", "master")
    other = make_clone(origin, tmp_path / "other")
    return origin, local, other


def head_files(repo: Path) -> str:
    return run(repo, "show", "--name-status", "--format=", "HEAD")


def test_commits_and_pushes_only_sessions(repos):
    origin, local, _ = repos
    (local / "claude-sessions" / "old.md").unlink()
    (local / "claude-sessions" / "proj").mkdir()
    (local / "claude-sessions" / "proj" / "new.md").write_text("new\n")
    (local / "notes.md").write_text("unrelated edit\n")
    run(local, "add", "notes.md")

    assert commit_claude_sessions(repo=local) is True

    assert head_files(local).splitlines() == ["D\tclaude-sessions/old.md", "A\tclaude-sessions/proj/new.md"]
    assert "1 added, 0 modified, 1 deleted" in run(local, "log", "-1", "--format=%B")
    assert run(local, "rev-parse", "HEAD") == run(origin, "rev-parse", "master")
    # The unrelated staged change is still staged, not committed
    assert run(local, "diff", "--cached", "--name-only") == "notes.md"


def test_refuses_when_local_has_unpushed_commits(repos):
    origin, local, _ = repos
    (local / "notes.md").write_text("wip\n")
    run(local, "commit", "--quiet", "-am", "wip")
    (local / "claude-sessions" / "new.md").write_text("new\n")
    before = run(local, "rev-parse", "HEAD")

    with pytest.raises(PreconditionError, match="1 commit\\(s\\) not pushed"):
        commit_claude_sessions(repo=local)

    assert run(local, "rev-parse", "HEAD") == before
    assert run(local, "status", "--porcelain", "--", "claude-sessions") == "?? claude-sessions/new.md"


def test_fast_forwards_when_only_behind(repos):
    origin, local, other = repos
    (other / "notes.md").write_text("from other machine\n")
    run(other, "commit", "--quiet", "-am", "other")
    run(other, "push", "--quiet", "origin", "master")
    (local / "claude-sessions" / "new.md").write_text("new\n")

    assert commit_claude_sessions(repo=local) is True

    assert run(local, "log", "--format=%s", "-3").splitlines()[1:] == ["other", "init"]
    assert run(local, "rev-parse", "HEAD") == run(origin, "rev-parse", "master")


def test_noop_without_session_changes(repos):
    _, local, _ = repos
    (local / "notes.md").write_text("unrelated\n")
    before = run(local, "rev-parse", "HEAD")

    assert commit_claude_sessions(repo=local) is False
    assert run(local, "rev-parse", "HEAD") == before


def test_dry_run_changes_nothing(repos):
    _, local, _ = repos
    (local / "claude-sessions" / "new.md").write_text("new\n")
    before = run(local, "rev-parse", "HEAD")

    assert commit_claude_sessions(repo=local, dry_run=True) is True
    assert run(local, "rev-parse", "HEAD") == before
    assert run(local, "status", "--porcelain", "--", "claude-sessions") == "?? claude-sessions/new.md"


def test_refuses_on_other_branch(repos):
    _, local, _ = repos
    run(local, "checkout", "--quiet", "-b", "feature")
    with pytest.raises(PreconditionError, match="on branch 'feature'"):
        commit_claude_sessions(repo=local)
