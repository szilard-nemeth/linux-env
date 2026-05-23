# Moving large files out of a git repository

Offload oversized binary files from a repo to external storage, leaving `.MOVED.txt` placeholders in their place.

## When to use this

Use this workflow when cleaning up a repository that accumulated large archives (`.tar.gz`, `.zip`, etc.) in the working tree. Two modes:

- **`--scan-working-tree`** — find large tracked files on disk now (most common)
- **`--commit`** — analyze files changed in a specific commit (useful when you know which commit introduced bulk)

## Quick start

### Scan working tree (recommended)

```bash
# 1. Preview what would be moved
git-move-large-files \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private \
  --dry-run

# 2. Move files and stage git changes
git-move-large-files \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private \
  --execute --stage

# 3. Review and commit manually
cd ~/development/my-repos/knowledge-base-private && git status
```

### Single commit

```bash
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --dry-run
```

(`git-move-large-files` is defined in `scripts/git.sh`.)

Output files land in `~/Downloads/git-large-files-<label>/` by default (`working-tree` or commit hash). Override with `--out-dir`.

## Examples

### Shell function (after sourcing `scripts/git.sh`)

```bash
# Scan all tracked files on disk (default use case)
git-move-large-files \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private

# Scan + custom output directory
git-move-large-files \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private \
  --out-dir ~/Downloads/git-cleanup-kb-private/part2 \
  --dry-run

# Scan, move, and stage
git-move-large-files \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private \
  --execute --stage

# Single commit — files changed in that commit
git-move-large-files \
  --commit 6619c839 \
  --repo ~/development/my-repos/knowledge-base-private \
  --dry-run

# Raise size threshold to 50 MB
git-move-large-files \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private \
  --threshold-mb 50 \
  --dry-run

# Override offload destination and repo path prefix
git-move-large-files \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private \
  --offload-root ~/googledrive/development/KB-private-offloaded \
  --path-prefix cloudera/tasks/cde/ \
  --dry-run
```

### Direct Python invocation

```bash
python3 scripts/git/git_move_large_files.py --help

python3 scripts/git/git_move_large_files.py \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private \
  --dry-run

python3 scripts/git/git_move_large_files.py \
  --scan-working-tree \
  --repo ~/development/my-repos/knowledge-base-private \
  --out-dir ~/Downloads/git-cleanup-kb-private/part2 \
  --threshold-mb 20 \
  --execute --stage
```

### Output files (default `--out-dir`)

| File | Purpose |
|------|---------|
| `git-details-working-tree.txt` or `git-details-hash-<commit>.txt` | Raw size listing (working tree or commit) |
| `git-commit-size-analyzer-out-*.txt` | Analyzer summary (top N + stats) |
| `git-commit-analyzer-all-results-sorted.txt` | Full sorted list fed to the mover |
| `git-large-file-mover-out-*.txt` | Move dry-run or execute log — **review before `--execute`** |
| `git-stage-summary.txt` | Staged changes summary (with `--stage`) |
| `contents-MOVED-files.txt` | Placeholder file contents (with `--stage`) |

## Safety notes

- **Always dry-run first.** `--dry-run` is the default; pass `--execute` only after reviewing the mover output log.
- **Does not commit.** The script moves files and optionally stages changes (`--stage`); you commit manually after reviewing.
- **Extension filter.** Only `.tar.gz`, `.gz`, `.zip`, and `.gzip` files above the threshold are moved. Other large files are reported but skipped.
- **Offload destination.** Defaults to `~/googledrive/development/KB-private-offloaded`. Override with `--offload-root`.
- **`--stage` requires `--execute`.** Staging deleted files and MOVED placeholders only makes sense after a real move.

## Underlying tools

`git_move_large_files.py` orchestrates:

1. Working tree scan (`git ls-files` + file sizes) or `git-commit-size-detailed.sh` for a single commit
2. `GitCommitSizeAnalyzer` (in the same file) — sort by size; writes full sorted list
3. `GitLargeFileMover` (in the same file) — move files above threshold; `--execute` to run for real

The shell size script can still be run standalone if needed.
