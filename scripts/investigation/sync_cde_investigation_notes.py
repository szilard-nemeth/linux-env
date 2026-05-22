#!/usr/bin/env python3
import os
import shutil
import subprocess
from typing import Any
import fnmatch

import click
import re
from pathlib import Path


def is_excluded(name: str, excludes: set) -> bool:
    """Check if the given file or directory name matches any of the exclude patterns."""
    for pattern in excludes:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def _find_jira_id_in_path(src: Path) -> Any:
    jira_id = None
    for part in reversed(src.parts):
        if re.match(r"^[A-Za-z]+-\d+$", part):
            jira_id = part
            break

    if not jira_id:
        click.secho(
            "Error: Could not find a Jira ID (format: LETTERS-NUMBERS) in the directory path.", fg="red", err=True
        )
        raise click.Abort()
    return jira_id


@click.command()
@click.argument("directory", type=click.Path(file_okay=False))
@click.option(
    "--exclude",
    multiple=True,
    help="Files/dirs to exclude (supports wildcards, e.g., --exclude venv --exclude 'cursor_*')",
)
def main(directory, exclude):
    cde_base_path = Path.home() / "development/my-repos/knowledge-base-private/cloudera/tasks/cde"

    # If the user passed a relative path, assume it's relative to the CDE base path
    src = Path(directory)
    if not src.is_absolute():
        src = cde_base_path / src

    src = src.resolve()

    if not src.exists():
        click.secho(f"Error: Directory '{src}' does not exist.", fg="red", err=True)
        raise click.Abort()

    # Validation 1: Base path hardcoded
    if not str(src).startswith(str(cde_base_path)):
        click.secho(f"Error: Directory must be under {cde_base_path}", fg="red", err=True)
        raise click.Abort()

    jira_id = _find_jira_id_in_path(src)

    kb_private_repo = Path.home() / "development/my-repos/knowledge-base-private"

    # Require source files to be committed in KB private repo first
    click.secho("Checking for uncommitted changes in the source repository...", fg="cyan")

    # Check if there are any uncommitted changes in the source directory
    status_check = subprocess.run(
        ["git", "status", "--porcelain", str(src)], cwd=kb_private_repo, capture_output=True, text=True
    )

    if status_check.stdout.strip():
        click.secho(f"\nError: The source directory ({src}) has uncommitted changes.", fg="red", err=True)
        click.secho("Please commit or stash your changes in the knowledge-base-private repository first.", fg="yellow")

        # Show what files are changed
        click.secho("\nChanged files:", fg="yellow")
        for line in status_check.stdout.splitlines():
            click.echo(f"  {line}")

        raise click.Abort()

    click.secho("No uncommitted changes in source repo.", fg="green")

    # Get the latest commit hash from source repo
    source_hash_proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=kb_private_repo, capture_output=True, text=True)
    source_hash = source_hash_proc.stdout.strip()

    dest_base = Path.home() / "development/cloudera/my-repos/task-notes"
    # Create the destination inside a Jira ID directory so different tickets don't overwrite each other
    dest = dest_base / jira_id / src.name

    dest.mkdir(parents=True, exist_ok=True)
    excludes = set(exclude)

    # TODO add warnings for excludes
    # 1. Copy files and warn on overwrite
    for root, dirs, files in os.walk(src):
        # Modify dirs in-place to skip excluded directories using glob matching
        dirs[:] = [d for d in dirs if not is_excluded(d, excludes)]

        for f in files:
            if is_excluded(f, excludes):
                continue

            src_file = Path(root) / f
            dest_file = dest / src_file.relative_to(src)

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            if dest_file.exists():
                click.secho(f"Warning: Overwriting {dest_file}", fg="yellow")

            shutil.copy2(src_file, dest_file)

    # 2. Git operations for destination
    subprocess.run(["git", "add", str(dest)], cwd=dest_base)

    diff_check_dest = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=dest_base)
    if diff_check_dest.returncode == 0:
        click.secho("\nNo changes to sync to target repository.", fg="green")
        return

    # Write colored diff of the staged changes to a file
    diff_file_dest = "/tmp/sync_investigation_diff_dest.txt"
    with open(diff_file_dest, "w") as f:
        subprocess.run(["git", "diff", "--cached", "--color=always"], cwd=dest_base, stdout=f)

    click.secho(f"\nColored diff saved to {diff_file_dest}", fg="cyan")
    click.secho("To view it, run:", fg="cyan")
    click.echo(f"  less -R {diff_file_dest}")

    # 3. Ask for confirmation and commit
    if click.confirm("\nCommit these changes to target repo?"):
        commit_msg = f"Auto-sync {jira_id} notes\n\nSource-Commit: {source_hash}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=dest_base)

        # 4. Print push commands
        click.secho("\nRun the following to push:", fg="green")
        click.echo(f"cd {dest_base} && git push origin HEAD")


if __name__ == "__main__":
    main()
