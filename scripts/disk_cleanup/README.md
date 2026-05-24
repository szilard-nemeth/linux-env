# Disk cleanup

[`cleanup_disk.py`](cleanup_disk.py) runs interactive disk cleanup tools. Each tool scans and reports what it would clean during a prepare phase; in normal mode you get one summary table and a single confirmation before anything is deleted. Use `--dry-run` to preview only (no prompts, no changes). Detailed logs are written under `~/snemeth-dev-projects/cleanup_disk/`.

## Default run

Cleans Maven cache, old Go SDK installs, Docker images, stale Python venvs and Terraform dirs, pip cache, and Poetry cache:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py
```

Preview reclaimable space without making changes:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --dry-run
```

Skip the confirmation prompt:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --force
```

Skip one or more tools (names match the plan table; repeatable):

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --dry-run --exclude-tool "Python Venvs"
poetry run python scripts/disk_cleanup/cleanup_disk.py --exclude-tool "Python Venvs" --exclude-tool docker-cleanup
```

List tool names and slugs for `--exclude-tool`:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --list-tools
```

## Single-tool modes

Use one of these flags to run a single cleanup tool instead of the default batch:

| Flag | What it runs |
|------|----------------|
| `--docker-only` | Remove dangling Docker images and unused images older than the time limit (default: 60 days). Also available as `docker-cleanup-auto` in [`scripts/docker.sh`](../docker.sh). |
| `--docker-system-prune-only` | Aggressive `docker system prune -a --volumes` |
| `--kb-private-git-offload` | Offload large tracked archives from `knowledge-base-private` to Google Drive |

Example — preview KB private git offload:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --kb-private-git-offload --dry-run
```

Run it for real (one confirmation after the plan table):

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --kb-private-git-offload
```

This scans the working tree for tracked archive files above 20 MB (`.tar.gz`, `.zip`, etc.), previews what would be moved, and on confirmation moves them to `~/googledrive/development/KB-private-offloaded`. Git changes are **not** staged automatically; review `git status` in the repo and commit when ready. For commit-based analysis, staging, and other options, use [`git_move_large_files.py`](../git/git_move_large_files.py) directly — see [`scripts/git/git-workflow-for-moving-large-files.md`](../git/git-workflow-for-moving-large-files.md).
