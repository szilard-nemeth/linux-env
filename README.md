[![CI](https://github.com/szilard-nemeth/linux-env/actions/workflows/ci.yml/badge.svg)](https://github.com/szilard-nemeth/linux-env/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/szilard-nemeth/linux-env/branch/master/graph/badge.svg)](https://codecov.io/gh/szilard-nemeth/linux-env)
[![CodeQL](https://github.com/szilard-nemeth/linux-env/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/szilard-nemeth/linux-env/actions/workflows/codeql-analysis.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![GitHub language count](https://img.shields.io/github/languages/count/szilard-nemeth/linux-env)

# My Linux / Mac environment

## Installation

Configure precommit as described in this blogpost: https://ljvmiranda921.github.io/notebook/2018/06/21/precommits-using-black-and-flake8/
Commands:
1. Install precommit: `pip install pre-commit`
2. Make sure to add pre-commit to your path. For example, on a Mac system, pre-commit is installed here: 
   `$HOME/Library/Python/3.8/bin/pre-commit`.
2. Execute `pre-commit install` to install git hooks in your `.git/` directory.

## Testing

Python tests use [Poetry](https://python-poetry.org/) 2.x and [pytest](https://docs.pytest.org/). Shell tests live under `tests/`.

### Prerequisites

- Python 3.9 or newer
- Poetry 2.x (`pip install "poetry>=2.0,<3.0"`)

### Install dependencies

From the repo root:

```bash
poetry install --only main,dev
```

This installs runtime and dev dependencies. The optional `localdev` group (sibling repos such as `python-commons`) is not required for tests.

### Run Python tests

```bash
poetry run python -m pytest
```

Pytest is configured in `pyproject.toml` to collect tests from `scripts/git` and `scripts/disk_cleanup`.

With coverage (same as CI):

```bash
mkdir -p junit
poetry run python -m pytest \
  --junitxml=junit/test-results.xml \
  --cov=scripts/git \
  --cov=scripts/disk_cleanup \
  --cov-report=xml \
  --cov-report=html
```

Coverage HTML is written to `htmlcov/`. JUnit XML goes to `junit/test-results.xml`.

### Run shell tests

```bash
find tests -type f \( -name "*.sh" -o -name "*.zsh" \) -exec chmod +x {} \;
find tests -type f \( -name "*.sh" -o -name "*.zsh" \) -print0 | while IFS= read -r -d '' script; do
  echo "Running $script..."
  "$script"
done
```

On Ubuntu/Debian, install `zsh` first if needed (`sudo apt-get install -y zsh`).

## Disk cleanup

[`scripts/disk_cleanup/cleanup_disk.py`](scripts/disk_cleanup/cleanup_disk.py) runs interactive disk cleanup tools. Each tool dry-runs first, prompts for confirmation (unless `--force`), then performs the cleanup and reports reclaimed space. Detailed logs are written under `~/snemeth-dev-projects/cleanup_disk/`.

### Default run

Cleans Maven cache, old Go SDK installs, Docker images, stale Python venvs and Terraform dirs, pip cache, and Poetry cache:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py
```

Skip confirmation prompts:

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --force
```

### Single-tool modes

Use one of these flags to run a single cleanup tool instead of the default batch:

| Flag | What it runs |
|------|----------------|
| `--docker-only` | Remove dangling Docker images and unused images older than the time limit (default: 60 days). Also available as `docker-cleanup-auto` in [`scripts/docker.sh`](scripts/docker.sh). |
| `--docker-system-prune-only` | Aggressive `docker system prune -a --volumes` |
| `--kb-private-git-offload` | Offload large tracked archives from `knowledge-base-private` to Google Drive |

Example — KB private git offload (dry-run preview, then confirm):

```bash
poetry run python scripts/disk_cleanup/cleanup_disk.py --kb-private-git-offload
```

This scans the working tree for tracked archive files above 20 MB (`.tar.gz`, `.zip`, etc.), previews what would be moved, and on confirmation moves them to `~/googledrive/development/KB-private-offloaded`. Git changes are **not** staged automatically; review `git status` in the repo and commit when ready. For commit-based analysis, staging, and other options, use [`git_move_large_files.py`](scripts/git/git_move_large_files.py) directly — see [`scripts/git/git-workflow-for-moving-large-files.md`](scripts/git/git-workflow-for-moving-large-files.md).

## Troubleshooting

### pre-commit installation
In case you're facing a similar issue:
```
An error has occurred: InvalidManifestError: 
=====> /<userhome>/.cache/pre-commit/repoBP08UH/.pre-commit-hooks.yaml does not exist
Check the log at /<userhome>/.cache/pre-commit/pre-commit.log
```
, please run: `pre-commit autoupdate`
More info here: https://github.com/pre-commit/pre-commit/issues/577