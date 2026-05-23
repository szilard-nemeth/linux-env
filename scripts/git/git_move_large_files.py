#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent


def msg(text: str = "") -> None:
    print(text)


def verify_commit(repo: Path, commit: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{commit}^{{commit}}"],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"Error: commit '{commit}' not found in repository '{repo}'.", file=sys.stderr)
        sys.exit(1)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a commit for large files, optionally offload them, and optionally stage git changes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s --commit 6619c839 --repo ~/development/my-repos/knowledge-base-private --dry-run
  %(prog)s --commit 6619c839 --repo ~/development/my-repos/knowledge-base-private --execute --stage
""",
    )
    parser.add_argument("--commit", required=True, help="Commit hash to analyze")
    parser.add_argument("--repo", required=True, type=Path, help="Local git repository root")
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Directory for intermediate output files (default: ~/Downloads/git-large-files-<commit>)",
    )
    parser.add_argument(
        "--threshold-mb",
        type=int,
        default=20,
        help="Minimum file size in MB to move (default: 20)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="execute",
        action="store_false",
        help="Preview moves without changing files (default)",
    )
    mode.add_argument(
        "--execute",
        dest="execute",
        action="store_true",
        help="Actually move files to offloaded storage",
    )
    parser.set_defaults(execute=False)
    parser.add_argument(
        "--stage",
        action="store_true",
        help="After moving, stage git rm/add for deleted files and MOVED placeholders",
    )
    parser.add_argument("--drive-root", help="Offload destination (passed to git_large_file_mover.py)")
    parser.add_argument(
        "--path-prefix",
        dest="path_prefix",
        help="Repository path prefix to strip before offload",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    execute = args.execute
    repo = args.repo.expanduser().resolve()
    commit = args.commit

    if args.stage and not execute:
        print("Error: --stage requires --execute (nothing to stage after a dry run).", file=sys.stderr)
        sys.exit(1)

    if args.out_dir:
        out_dir = args.out_dir.expanduser().resolve()
    else:
        out_dir = Path.home() / "Downloads" / f"git-large-files-{commit}"
    out_dir.mkdir(parents=True, exist_ok=True)

    verify_commit(repo, commit)

    details_out = out_dir / f"git-details-hash-{commit}.txt"
    analyzer_out = out_dir / f"git-commit-size-analyzer-out-{commit}.txt"
    all_sorted_out = out_dir / "git-commit-analyzer-all-results-sorted.txt"
    mover_out = out_dir / f"git-large-file-mover-out-{commit}.txt"
    stage_summary_out = out_dir / "git-stage-summary.txt"
    moved_contents_out = out_dir / "contents-MOVED-files.txt"

    msg(f"Repository: {repo}")
    msg(f"Commit: {commit}")
    msg(f"Output directory: {out_dir}")
    msg(f"Threshold: {args.threshold_mb}MB")
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
        threshold_mb=args.threshold_mb,
        repo=repo,
        execute=execute,
        drive_root=args.drive_root,
        path_prefix=args.path_prefix,
    )
    msg(f"  Wrote {mover_out}")

    if args.stage:
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
