# Disk cleanup

[`cleanup_disk.py`](cleanup_disk.py) runs interactive disk cleanup tools. Each tool dry-runs first, prompts for confirmation (unless `--force`), then performs the cleanup and reports reclaimed space. Detailed logs are written under `~/snemeth-dev-projects/cleanup_disk/`.

## Default run

Cleans Maven cache, old Go SDK installs, Docker images, stale Python venvs and Terraform dirs, pip cache, and Poetry cache:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py
```

Skip confirmation prompts:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --force
```

## Single-tool modes

Use one of these flags to run a single cleanup tool instead of the default batch:

| Flag | What it runs |
|------|----------------|
| `--docker-only` | Remove dangling Docker images and unused images older than the time limit (default: 60 days). Also available as `docker-cleanup-auto` in [`scripts/docker.sh`](../docker.sh). |
| `--docker-system-prune-only` | Aggressive `docker system prune -a --volumes` |
| `--kb-private-git-offload` | Offload large tracked archives from `knowledge-base-private` to Google Drive |

Example — KB private git offload (dry-run preview, then confirm):

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --kb-private-git-offload
```

This scans the working tree for tracked archive files above 20 MB (`.tar.gz`, `.zip`, etc.), previews what would be moved, and on confirmation moves them to `~/googledrive/development/KB-private-offloaded`. Git changes are **not** staged automatically; review `git status` in the repo and commit when ready. For commit-based analysis, staging, and other options, use [`git_move_large_files.py`](../git/git_move_large_files.py) directly — see [`scripts/git/git-workflow-for-moving-large-files.md`](../git/git-workflow-for-moving-large-files.md).
