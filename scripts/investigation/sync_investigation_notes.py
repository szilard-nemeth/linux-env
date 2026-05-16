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

    jira_id = _find_jira_id_in_path(src)

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

    # 2. Git operations
    subprocess.run(["git", "add", str(dest)], cwd=dest_base)

    # Write colored diff of the staged changes to a file
    diff_file = "/tmp/sync_investigation_diff.txt"
    with open(diff_file, "w") as f:
        subprocess.run(["git", "diff", "--cached", "--color=always"], cwd=dest_base, stdout=f)

    click.secho(f"\nColored diff saved to {diff_file}", fg="cyan")
    click.secho("To view it, run:", fg="cyan")
    click.echo(f"  less -R {diff_file}")

    # 3. Ask for confirmation and commit
    if click.confirm("\nCommit these changes?"):
        commit_msg = f"Auto-sync {jira_id} notes"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=dest_base)

        # 4. Print push commands
        click.secho("\nRun the following to push:", fg="green")
        click.echo(f"cd {dest_base} && git push origin HEAD")


if __name__ == "__main__":
    main()
