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

See [scripts/disk_cleanup/README.md](scripts/disk_cleanup/README.md) for usage of [`cleanup_disk.py`](scripts/disk_cleanup/cleanup_disk.py).

## Git: moving large files out of a repo

See [scripts/git/git-workflow-for-moving-large-files.md](scripts/git/git-workflow-for-moving-large-files.md) for offloading large archives from a git working tree or specific commits via [`git_move_large_files.py`](scripts/git/git_move_large_files.py). Run it with `poetry run python scripts/git/git_move_large_files.py ...` from this repo so dependencies are available.

## Claude session exporter

The `export_claude_sessions.py` script (and its `session_rename_report.py` companion) has been extracted to its own repository:

- https://github.com/szilard-nemeth/claude-code-tools

Full history was preserved via `git-filter-repo`. It is registered as the `claude_code_tools` external repo in [`config/external-repos.json`](config/external-repos.json), checked out at `~/development/my-repos/claude-code-tools/`. The `claude-export` / `claude-export-force` commands run `scripts/external-repos.py ensure claude_code_tools` first, which clones the repo if it is missing, so there's no manual setup step.

## Shell startup performance

Every new terminal tab runs `.zprofile`, `.zshrc` and `setup-env.sh`, so anything slow in them is paid on every tab. In October 2026 a new tab took ~7.6 s; it now takes ~1.2 s.

Measuring:

| Command | Answers |
|---|---|
| `hyperfine -w 2 -r 10 -N 'zsh -li -c exit' 'zsh -f -c exit'` | How slow is startup overall, compared to bare zsh? |
| `LINUXENV_PROFILE=1 zsh -li -c exit 2>&1 >/dev/null \| grep -aE "ms  "` | How long does each phase / sourced file take? |
| `LINUXENV_ZPROF=1 zsh -li -c exit; head -30 /tmp/zprof.txt` | Which functions are slow? |
| `PS4='+%D{%s.%6.} %N:%i> ' zsh -lix -c exit 2> /tmp/trace.log` | Which exact lines are slow? (sort the gaps between timestamps) |

Rules for anything that runs at startup:

- No network or daemon calls (`git fetch`, `docker`, ...). Check cheap local state first (a stamp file, `nc -z` on a port) and offer a `*_FORCE*` env var.
- Don't redo idempotent work. The repo to home copy only runs when `find ... -newer ~/.env/.last-copy` finds a change (force it with `LINUXENV_FORCE_COPY=1`).
- Don't `eval "$(tool ...)"` or `$(tool --completion ...)` directly. Use `linuxenv-cached-source <name> <dependency-file> <cmd...>` from [`scripts/startup-cache.sh`](scripts/startup-cache.sh), which caches the output in `~/.cache/linuxenv/` until the dependency file changes (`linuxenv-cache-clear` wipes it).
- Count forks: each process costs 20–70 ms here. Prefer `$HOMEBREW_PREFIX` over `brew --prefix`, `${var##*/}` over `$(basename ...)`, one `sed` over `xargs -n1`.
- Only one `compinit` (in `.zshrc`, with `-C`).
- Don't `cd` at startup (it fires chpwd hooks); use `$(cd dir && cmd)`.
- Cache in files, not env vars: new kitty tabs don't inherit a sibling shell's environment.
- The last command of an rc file must not return non-zero, or the first prompt shows `<1>`.

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

### black hook: `ModuleNotFoundError: No module named 'typing_extensions'`

If the `black` pre-commit hook fails on commit with a traceback like:

```
File ".../site-packages/black/cache.py", line 21, in <module>
    from typing_extensions import Self
ModuleNotFoundError: No module named 'typing_extensions'
```

this is not a lint failure — black's own pre-commit venv is corrupted/incomplete (observed with `black 24.8.0`). Fix by clearing the pre-commit cache so the hook environments are rebuilt from scratch:

```bash
pre-commit clean
pre-commit install --install-hooks
```

If it still fails after that, force-reinstall by removing the specific hook env directory printed in the traceback (the `repoXXXXXX` path under `~/.cache/pre-commit/`), then re-run:

```bash
rm -rf ~/.cache/pre-commit/repoXXXXXX   # use the path from the traceback
pre-commit run black --all-files
```