#!/usr/bin/env python3

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import click

SCRIPT_DIR = Path(__file__).resolve().parent


def msg(text: str = "") -> None:
    print(text)


def verify_commit(repo: Path, commit: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{commit}^{{commit}}"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise click.ClickException(f"commit '{commit}' not found in repository '{repo}'.")


def run_commit_size_detailed(repo: Path, commit: str, output_path: Path) -> None:
    script = SCRIPT_DIR / "git-commit-size-detailed.sh"
    with output_path.open("w") as out:
        subprocess.run(
            [str(script), commit],
            cwd=repo,
            stdout=out,
            check=True,
        )


def run_analyzer(details_path: Path, analyzer_out: Path, all_sorted_out: Path) -> None:
    with analyzer_out.open("w") as out:
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "git_commit_size_analyzer.py"),
                str(details_path),
                "--all-sorted-out",
                str(all_sorted_out),
            ],
            stdout=out,
            check=True,
        )


def run_mover(
    all_sorted_out: Path,
    mover_out: Path,
    *,
    threshold_mb: int,
    repo: Path,
    execute: bool,
    drive_root: Optional[str],
    path_prefix: Optional[str],
) -> None:
    args = [
        sys.executable,
        str(SCRIPT_DIR / "git_large_file_mover.py"),
        str(all_sorted_out),
        str(threshold_mb),
        "--repo",
        str(repo),
    ]
    if execute:
        args.append("--execute")
    if drive_root:
        args.extend(["--drive-root", drive_root])
    if path_prefix:
        args.extend(["--path-prefix-to-strip", path_prefix])

    with mover_out.open("w") as out:
        subprocess.run(args, stdout=out, check=True)


def stage_changes(repo: Path, stage_summary_out: Path, moved_contents_out: Path) -> None:
    deleted = subprocess.check_output(
        ["git", "ls-files", "--deleted"],
        cwd=repo,
        text=True,
    ).strip()
    if deleted:
        subprocess.run(
            ["git", "rm", *deleted.splitlines()],
            cwd=repo,
            check=True,
        )

    for path in repo.rglob("*MOVED*"):
        if "REMOVED" in path.name:
            continue
        rel = path.relative_to(repo)
        subprocess.run(["git", "add", str(rel)], cwd=repo, check=True)

    status = subprocess.check_output(
        ["git", "status", "--short"],
        cwd=repo,
        text=True,
    )
    summary_lines = [line for line in status.splitlines() if re.search(r"deleted|^\?\?|^A ", line)]
    stage_summary_out.write_text("\n".join(summary_lines) + ("\n" if summary_lines else ""))

    cached = subprocess.check_output(
        ["git", "diff", "--name-only", "--cached"],
        cwd=repo,
        text=True,
    ).splitlines()
    moved_names = [name for name in cached if "MOVED" in name]

    parts: List[str] = []
    for filename in moved_names:
        parts.append(f"Processing file: {filename}")
        parts.append((repo / filename).read_text())
        parts.append("")
    moved_contents_out.write_text("\n".join(parts))


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--commit", required=True, help="Commit hash to analyze")
@click.option(
    "--repo",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Local git repository root",
)
@click.option(
    "--out-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory for intermediate output files (default: ~/Downloads/git-large-files-<commit>)",
)
@click.option(
    "--threshold-mb",
    default=20,
    show_default=True,
    help="Minimum file size in MB to move",
)
@click.option(
    "--execute/--dry-run",
    "execute",
    default=False,
    show_default=True,
    help="Actually move files to offloaded storage, or preview moves (default)",
)
@click.option(
    "--stage",
    is_flag=True,
    help="After moving, stage git rm/add for deleted files and MOVED placeholders",
)
@click.option("--drive-root", help="Offload destination (passed to git_large_file_mover.py)")
@click.option(
    "--path-prefix",
    help="Repository path prefix to strip before offload",
)
def main(
    commit: str,
    repo: Path,
    out_dir: Optional[Path],
    threshold_mb: int,
    execute: bool,
    stage: bool,
    drive_root: Optional[str],
    path_prefix: Optional[str],
) -> None:
    """Analyze a commit for large files, optionally offload them, and optionally stage git changes."""
    if stage and not execute:
        raise click.UsageError("--stage requires --execute (nothing to stage after a dry run).")

    repo = repo.expanduser().resolve()

    if out_dir:
        resolved_out_dir = out_dir.expanduser().resolve()
    else:
        resolved_out_dir = Path.home() / "Downloads" / f"git-large-files-{commit}"
    resolved_out_dir.mkdir(parents=True, exist_ok=True)

    verify_commit(repo, commit)

    details_out = resolved_out_dir / f"git-details-hash-{commit}.txt"
    analyzer_out = resolved_out_dir / f"git-commit-size-analyzer-out-{commit}.txt"
    all_sorted_out = resolved_out_dir / "git-commit-analyzer-all-results-sorted.txt"
    mover_out = resolved_out_dir / f"git-large-file-mover-out-{commit}.txt"
    stage_summary_out = resolved_out_dir / "git-stage-summary.txt"
    moved_contents_out = resolved_out_dir / "contents-MOVED-files.txt"

    msg(f"Repository: {repo}")
    msg(f"Commit: {commit}")
    msg(f"Output directory: {resolved_out_dir}")
    msg(f"Threshold: {threshold_mb}MB")
    msg(f"Mode: {'EXECUTE (files will be moved)' if execute else 'DRY RUN (preview only)'}")
    msg()

    msg("Step 1/3: Collecting file sizes from commit...")
    run_commit_size_detailed(repo, commit, details_out)
    msg(f"  Wrote {details_out}")

    msg("Step 2/3: Sorting files by size...")
    run_analyzer(details_out, analyzer_out, all_sorted_out)
    msg(f"  Wrote {analyzer_out}")
    msg(f"  Wrote {all_sorted_out}")

    msg("Step 3/3: Processing large files...")
    run_mover(
        all_sorted_out,
        mover_out,
        threshold_mb=threshold_mb,
        repo=repo,
        execute=execute,
        drive_root=drive_root,
        path_prefix=path_prefix,
    )
    msg(f"  Wrote {mover_out}")

    if stage:
        msg()
        msg("Staging git changes...")
        stage_changes(repo, stage_summary_out, moved_contents_out)
        msg(f"  Wrote {stage_summary_out}")
        msg(f"  Wrote {moved_contents_out}")
        msg()
        msg(f"Review staged changes in {repo}, then commit when ready:")
        msg(f"  cd {repo} && git status")

    msg()
    if execute:
        msg("Done. Files were moved.")
    else:
        msg(f"Dry run complete. Review {mover_out}, then re-run with --execute.")


if __name__ == "__main__":
    main()
