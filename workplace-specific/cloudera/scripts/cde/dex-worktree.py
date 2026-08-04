#!/usr/bin/env python3
"""
dex-worktree — thin wrapper around `git worktree` for the dex repo.

Creates (or reuses) a git worktree under:
    ~/development/cloudera/cde/dex/<name>

The primary dex checkout lives at ~/development/cloudera/cde/dex and is the
"main" worktree — every `git worktree` command below is run from there.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click


# --- Config ------------------------------------------------------------------

DEX_REPO = Path.home() / "development" / "cloudera" / "cde" / "dex"
WORKTREE_ROOT = DEX_REPO  # new worktrees are placed as subdirs of the main checkout


@dataclass
class WorktreeEntry:
    """One entry from `git worktree list --porcelain`.

    `branch` is the short name (e.g. "master") when HEAD is on a branch, or
    the empty string when the worktree is detached — callers should treat
    an empty `branch` as "(detached)".
    """

    worktree: str
    head: str
    branch: str

    @classmethod
    def from_porcelain(cls, raw: dict[str, str]) -> "WorktreeEntry":
        """Build an entry from one porcelain stanza.

        Handles the format's quirks in one place:
        - `HEAD` in the raw dict maps to the `head` field.
        - Bare keywords like `detached` / `bare` appear as keys we ignore.
        - `branch` values arrive as `refs/heads/<name>`; we store the short name.
        Missing keys default to "" so a detached-HEAD stanza still parses.
        """
        return cls(
            worktree=raw.get("worktree", ""),
            head=raw.get("HEAD", ""),
            branch=raw.get("branch", "").removeprefix("refs/heads/"),
        )


# --- git helpers -------------------------------------------------------------


def _run(cmd: list[str], cwd: Path, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command, echoing it so the user sees what git is doing."""
    click.echo(f"$ (cd {cwd}) {' '.join(cmd)}", err=True)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=check,
        text=True,
        capture_output=capture,
    )


def _worktree_list(repo: Path) -> list[WorktreeEntry]:
    """Return `git worktree list --porcelain` parsed into WorktreeEntry objects.

    Porcelain output is one stanza per worktree — `<key> <value>` lines and
    bare keywords like `detached` / `bare`, terminated by a blank line. We
    collect each stanza into a dict and hand it to WorktreeEntry.from_porcelain,
    which owns the git-format quirks.
    """
    proc = _run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo,
        capture=True,
    )
    entries: list[WorktreeEntry] = []
    raw: dict[str, str] = {}

    def _flush() -> None:
        if raw:
            entries.append(WorktreeEntry.from_porcelain(raw))
            raw.clear()

    for line in proc.stdout.splitlines():
        if not line.strip():
            _flush()
            continue
        if " " in line:
            key, value = line.split(" ", 1)
        else:
            # Bare keywords like `detached` or `bare` — record with empty value.
            key, value = line, ""
        raw[key] = value
    _flush()
    return entries


def _find_worktree_by_path(entries: list[WorktreeEntry], path: Path) -> Optional[WorktreeEntry]:
    resolved = Path(path).resolve().as_posix()
    for e in entries:
        if e.worktree and Path(e.worktree).resolve().as_posix() == resolved:
            return e
    return None


def _branch_exists(repo: Path, branch: str) -> bool:
    proc = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=str(repo),
    )
    return proc.returncode == 0


# --- CLI ---------------------------------------------------------------------

INFO_TEXT = """\
Git worktree commands this script uses (with brief notes)
==========================================================

All commands are run from the main dex checkout:
    {repo}

1) git worktree list --porcelain
     Machine-readable list of all worktrees registered with this repo.
     The primary checkout is the first entry; every `git worktree add`
     appends another. Output blocks look like:
         worktree /path/to/wt
         HEAD <sha>
         branch refs/heads/<branch>
     A `detached` line replaces `branch` when HEAD isn't on a branch.

2) git show-ref --verify --quiet refs/heads/<branch>
     Silent probe: exits 0 if the branch exists locally, non-zero otherwise.
     Used here to decide whether to check out an existing branch or create
     a new one when adding the worktree.

3) git worktree add <path> <branch>
     Attach an existing local branch to a new working tree at <path>.
     The branch can only be checked out in one worktree at a time — if it
     is already checked out elsewhere, git refuses.

4) git worktree add -b <branch> <path> [<start-point>]
     Create a new branch (default start point: current HEAD) AND check it
     out into a new worktree in one step. Used when the requested name
     doesn't correspond to an existing branch.

Handy commands this script does NOT run, but you should know:

  git worktree remove <path>
     Delete a worktree's directory and unregister it. Refuses if the
     worktree has uncommitted changes; add --force to override.

  git worktree prune
     Clean up admin records for worktrees whose directories were deleted
     out-of-band (e.g. `rm -rf`).

  git worktree move <path> <new-path>
     Relocate a worktree on disk without losing its git registration.

  git worktree lock <path> [--reason <text>]
  git worktree unlock <path>
     Mark a worktree as locked so `remove`/`prune` refuse to touch it —
     useful for worktrees on removable media.

Mental model:
  A worktree is a second checkout of the same repository. It shares the
  object database (.git/objects) with the main clone but has its own
  index, HEAD, and working files. Each branch may only be checked out in
  one worktree at a time.
"""


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("name", required=False)
@click.option("--list", "list_", is_flag=True, help="List existing worktrees for the dex repo and exit.")
@click.option("--info", is_flag=True, help="Print the git worktree commands this script uses and exit.")
@click.option(
    "--start-point",
    default=None,
    help="When creating a new branch, branch from this ref " "(default: current HEAD of the main checkout).",
)
def main(name: str | None, list_: bool, info: bool, start_point: str | None) -> None:
    """Create or reuse a git worktree under ~/development/cloudera/cde/dex/<NAME>."""

    if info:
        click.echo(INFO_TEXT.format(repo=DEX_REPO))
        return

    if not DEX_REPO.is_dir():
        raise click.ClickException(f"dex repo not found at {DEX_REPO} — expected the main checkout there.")

    if list_:
        entries = _worktree_list(DEX_REPO)
        click.echo("")
        click.echo(f"Worktrees registered with {DEX_REPO}:")
        for e in entries:
            branch = e.branch or "(detached)"
            click.echo(f"  {branch:<40} {e.head[:10]}  {e.worktree or '?'}")
        return

    if not name:
        raise click.UsageError("NAME is required (unless --list or --info is used). " "Run with --help for usage.")

    target = WORKTREE_ROOT / name
    entries = _worktree_list(DEX_REPO)
    existing = _find_worktree_by_path(entries, target)

    if existing is not None:
        branch = existing.branch or "(detached)"
        click.secho(
            f"⚠  Worktree already exists at {target} (branch: {branch}). " f"Reusing it — not removing or recreating.",
            fg="yellow",
            err=True,
        )
        click.echo(str(target))
        return

    if target.exists():
        raise click.ClickException(
            f"{target} exists on disk but is not a registered worktree — "
            f"refusing to touch it. Remove it manually or pick another name."
        )

    if _branch_exists(DEX_REPO, name):
        click.echo(f"Branch '{name}' already exists — checking it out into a new worktree.")
        _run(["git", "worktree", "add", str(target), name], cwd=DEX_REPO)
    else:
        click.echo(f"Branch '{name}' does not exist — creating it with the new worktree.")
        cmd = ["git", "worktree", "add", "-b", name, str(target)]
        if start_point:
            cmd.append(start_point)
        _run(cmd, cwd=DEX_REPO)

    click.secho(f"✓ Worktree ready at {target}", fg="green")
    click.echo(str(target))


if __name__ == "__main__":
    main()
