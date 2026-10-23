# gh-pr-export-md

Export a single GitHub PR (metadata + issue comments + inline review threads)
as one Markdown file. Reuses your existing `gh` CLI auth, so it works against
enterprise GitHub without a separate token.

## Prerequisites

- `gh` installed and authenticated for the target host:
  ```bash
  gh auth login --hostname github.infra.cloudera.com
  gh auth status                 # confirm you're logged in
  ```
- Python 3 (uses stdlib only — no `pip install` needed).

## Usage

```bash
./gh-pr-export-md.py <owner/repo> <pr-number> [--host HOST] [--out FILE]
```

Defaults: `--host github.infra.cloudera.com`, `--out pr<N>.md` in the current
directory.

## Examples

Enterprise Cloudera PR (host default is already Cloudera's):

```bash
cd ~/development/my-repos/linux-env/scripts/git
./gh-pr-export-md.py CDH/dex 12345
# → writes ./pr12345.md
```

Public github.com PR, custom output path:

```bash
./gh-pr-export-md.py cli/cli 9876 --host github.com --out /tmp/cli-9876.md
```

Run from anywhere via the absolute path (no alias is wired up yet):

```bash
python3 ~/development/my-repos/linux-env/scripts/git/gh-pr-export-md.py CDH/dex 12345
```

## What the output contains

1. **Header** — title, PR URL, author, state (+ merged flag), base/head refs,
   short head SHA, created/updated timestamps, changed-file count, +/- diff
   totals.
2. **Description** — the PR body verbatim.
3. **Timeline** — issue comments and review submissions interleaved in
   chronological order, each with a link back to the GitHub anchor.
4. **Inline review threads** — review comments grouped by their root
   (`in_reply_to_id` chain), one section per `path:line`, replies in order.

## Why not `gh2md`?

[`mattduck/gh2md`](https://github.com/mattduck/gh2md) is a whole-repo
issues+PRs exporter — it cannot fetch a single PR by number, uses a raw PAT
instead of `gh` auth, and produces a flatter output. See the top-of-file
docstring for the design intent of this script.
