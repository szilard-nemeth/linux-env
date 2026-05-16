#!/usr/bin/env python3
import os
import shutil
import subprocess
import click
from pathlib import Path


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option(
    "--exclude", multiple=True, help="Files/dirs to exclude (use multiple times, e.g., --exclude venv --exclude .git)"
)
def main(directory, exclude):
    src = Path(directory)
    dest_base = Path.home() / "development/cloudera/my-repos/task-notes"
    dest = dest_base / src.name

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

    # Show colored diff of the staged changes
    subprocess.run(["git", "diff", "--cached", "--color=always"], cwd=dest_base)

    # 3. Ask for confirmation and commit
    if click.confirm("\nCommit these changes?"):
        commit_msg = f"Auto-sync {src.name} notes"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=dest_base)

        # 4. Print push commands
        click.secho("\nRun the following to push:", fg="green")
        click.echo(f"cd {dest_base} && git push origin HEAD")


if __name__ == "__main__":
    main()
