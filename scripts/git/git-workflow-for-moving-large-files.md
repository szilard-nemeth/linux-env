# Moving large files out of a git repository

Offload oversized binary files from a repo commit to Google Drive, leaving `.MOVED.txt` placeholders in their place.

## When to use this

Use this workflow when cleaning up a repository that accumulated large archives (`.tar.gz`, `.zip`, etc.) in git history or the working tree. Typical case: analyzing a specific commit that introduced bulky files, moving them to offloaded storage, and staging deletions plus placeholder files for a follow-up commit.

## Quick start

```bash
# 1. Preview what would be moved
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --dry-run

# 2. Move files and stage git changes
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --execute --stage

# 3. Review and commit manually
cd ~/development/my-repos/knowledge-base-private && git status
```

(`git-move-large-files` is defined in `scripts/git.sh`.)

Output files land in `~/Downloads/git-large-files-<commit>/` by default. Override with `--out-dir`.

## Examples

### Shell function (after sourcing `scripts/git.sh`)

```bash
# Dry run (default) — preview moves, write logs under ~/Downloads/git-large-files-<commit>/
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private

# Explicit dry run + custom output directory
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --out-dir ~/Downloads/git-cleanup-kb-private/part2 \
  --dry-run

# Move files only (no git staging)
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --execute

# Move files and stage deletions + MOVED placeholders
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --execute --stage

# Raise size threshold to 50 MB
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --threshold-mb 50 \
  --dry-run

# Override offload destination and repo path prefix
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --drive-root ~/googledrive/development/KB-private-offloaded \
  --path-prefix cloudera/tasks/cde/ \
  --dry-run
```

### Direct Python invocation

```bash
python3 scripts/git/git_move_large_files.py --help

python3 scripts/git/git_move_large_files.py \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --dry-run

python3 scripts/git/git_move_large_files.py \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --out-dir ~/Downloads/git-cleanup-kb-private/part2 \
  --threshold-mb 20 \
  --execute --stage
```

### Output files (default `--out-dir`)

| File | Purpose |
|------|---------|
| `git-details-hash-<commit>.txt` | Raw sizes from `git-commit-size-detailed.sh` |
| `git-commit-size-analyzer-out-<commit>.txt` | Analyzer summary (top N + stats) |
| `git-commit-analyzer-all-results-sorted.txt` | Full sorted list fed to the mover |
| `git-large-file-mover-out-<commit>.txt` | Move dry-run or execute log — **review before `--execute`** |
| `git-stage-summary.txt` | Staged changes summary (with `--stage`) |
| `contents-MOVED-files.txt` | Placeholder file contents (with `--stage`) |

## Safety notes

- **Always dry-run first.** `--dry-run` is the default; pass `--execute` only after reviewing `git-large-file-mover-out-<commit>.txt`.
- **Does not commit.** The script moves files and optionally stages changes (`--stage`); you commit manually after reviewing.
- **Extension filter.** Only `.tar.gz`, `.gz`, `.zip`, and `.gzip` files above the threshold are moved. Other large files are reported but skipped.
- **Offload destination.** Defaults to `~/googledrive/development/KB-private-offloaded`. Override with `--drive-root`.
- **`--stage` requires `--execute`.** Staging deleted files and MOVED placeholders only makes sense after a real move.

## Underlying tools

`git_move_large_files.py` orchestrates:

1. `git-commit-size-detailed.sh` — list changed files and sizes for a commit
2. `git_commit_size_analyzer.py` — sort by size; writes full sorted list via `--all-sorted-out`
3. `GitLargeFileMover` (in the same file) — move files above threshold; `--execute` to run for real

The analyzer and shell size script can still be run standalone if needed.
