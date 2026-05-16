#!/usr/bin/env python3
import os
import shutil
import subprocess
from typing import Any

import click
import re
from pathlib import Path


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
@click.argument("directory", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option(
    "--exclude", multiple=True, help="Files/dirs to exclude (use multiple times, e.g., --exclude venv --exclude .git)"
)
def main(directory, exclude):
    src = Path(directory)

    # Validation 1: Base path hardcoded
    cde_base_path = Path.home() / "development/my-repos/knowledge-base-private/cloudera/tasks/cde"
    if not str(src).startswith(str(cde_base_path)):
        click.secho(f"Error: Directory must be under {cde_base_path}", fg="red", err=True)
        raise click.Abort()

    jira_id = _find_jira_id_in_path(src)

    kb_private_repo = Path.home() / "development/my-repos/knowledge-base-private"

    # Require source files to be committed in KB private repo first
    click.secho("Checking for uncommitted changes in the source repository...", fg="cyan")
    # Add files in the source directory
    subprocess.run(["git", "add", str(src)], cwd=kb_private_repo)

    # Check if there are changes
    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=kb_private_repo)

    if diff_check.returncode != 0:
        # There are changes, need to commit them
        diff_file_src = "/tmp/sync_investigation_diff_src.txt"
        with open(diff_file_src, "w") as f:
            subprocess.run(["git", "diff", "--cached", "--color=always"], cwd=kb_private_repo, stdout=f)

        click.secho(f"\nUncommitted changes found in source repo. Colored diff saved to {diff_file_src}", fg="yellow")
        click.secho("To view it, run:", fg="cyan")
        click.echo(f"  less -R {diff_file_src}")

        if click.confirm("\nCommit these changes in KB private repo?"):
            commit_msg_src = f"Update notes for {jira_id}"
            subprocess.run(["git", "commit", "-m", commit_msg_src], cwd=kb_private_repo)
        else:
            click.secho("Error: Source files must be committed before copying.", fg="red", err=True)
            raise click.Abort()
    else:
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
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in excludes]

        for f in files:
            if f in excludes:
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
