# export_claude_sessions.py

Click-based CLI that incrementally exports Claude Code session transcripts
(`~/.claude/projects/<proj>/<session-id>.jsonl`) into the
`knowledge-base-private` repo as readable Markdown plus the raw `.jsonl`,
tracking what's been exported in a JSON state file so re-runs only copy what
changed.

## Quick start

```bash
# Inspect the current state without changing anything
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --dry-run

# Export everything that's new or changed
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py

# Export and git-commit the new transcripts
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --commit
```

The script takes no positional args and its defaults (`--projects-dir`,
`--dest-dir`, `--state-file`) are all absolute, so the exact same command
works from any working directory. Alias suggestion:

```bash
# in ~/.zshrc / ~/.bashrc
alias claude-export='python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py'
# then, from anywhere:
claude-export --commit           # export new/changed sessions and commit
claude-export --force --commit   # re-export everything and commit
```

## What it does

1. Walks `~/.claude/projects/*/*.jsonl`.
2. For each session, reads the jsonl once to extract:
   - **title** — the *latest* `custom-title` record if any (user-set via
     `/title`), otherwise the first `ai-title` (Claude Code's auto-generated
     title). Custom titles win because a user rename is always more meaningful
     than an auto-generated one.
   - first user prompt (fallback when no title exists)
   - earliest timestamp (used for the date prefix)
   - line count
3. Compares `source_mtime` against the recorded `source_mtime` in the state
   file. New or changed sessions are flagged for export.
4. Writes both `.md` (rendered transcript) and `.jsonl` (raw copy) into
   `~/development/my-repos/knowledge-base-private/claude-sessions/<project-slug>/`
   under the **deterministic short name**
   `<YYYY-MM-DD>-<slug>--<id8>` — e.g.
   `2026-07-16-dex-21945-spark-shs-tm-phase1-20260716-20260717--57bc07c7.md`.
5. Updates the state file.
6. Optionally commits the new transcripts to `knowledge-base-private`.

## Just want to see the state?

`--dry-run` prints the full status table and writes nothing:

```bash
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --dry-run
```

The table shows every session with these columns:

| Column                 | Meaning                                                    |
|------------------------|------------------------------------------------------------|
| Project                | Decoded project path                                       |
| Session (short name)   | The auto-derived slug + date + id8                         |
| Source path            | Raw jsonl under `~/.claude/projects/...`                   |
| State                  | ✓ fresh · ↻ stale (source newer than export) · ✗ never    |
| MTime                  | Source jsonl mtime                                         |
| Export location        | Path under `claude-sessions/...` if previously exported    |
| Lines                  | Total lines in the source jsonl                            |

`--dry-run` also previews any pending file renames from a prior naming scheme,
without performing them.

## Listing sessions (pipe-friendly)

`--list` prints every discovered session as TAB-separated rows and exits —
useful for finding a session id to plug into `--session-id`:

```
<session_id>  <mtime>  <lines>  <name>  <project_label>
```

```bash
# All sessions on the machine
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --list

# Filter down to something matchable — --filter also matches ai-title,
# custom-title, and the first user message, not just paths and ids
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --list --filter DEX-21945

# Grab just the UUIDs for scripting
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --list --filter livy | cut -f1
```

`name` is the AI-generated title (or user-set custom title if present),
falling back to the first user message, falling back to `-`.

## Exporting one session by id

`--session-id <ID>` exports exactly one session — accepts a full UUID or any
unambiguous prefix. It:

- errors out loudly if 0 matches or >1 matches (listing candidates so you can
  narrow the prefix)
- implies `--force` (single-session export is almost always "rewrite this now")

```bash
# From --list, grab the UUID (or a unique prefix) then:
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py \
    --session-id 57bc07c7 --commit
```

Chained one-liner:

```bash
uuid=$(python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py \
        --list --filter DEX-21945 | cut -f1 | head -1)
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py \
    --session-id "$uuid" --commit
```

## Filter to a subset

`--filter` narrows the set of sessions considered. It matches any of:
project label, project slug, session id, ai-title, custom-title, or first
user message (case-insensitive substring match).

```bash
# Only sessions whose title or path mentions 'livy'
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --dry-run --filter livy
```

## Force a full re-export

Useful after editing the markdown template, changing the metadata reader, or
wiping the destination:

```bash
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --force
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --force --filter linux-env  # subset
python3 ~/development/my-repos/linux-env/scripts/python/export_claude_sessions.py --force --dry-run           # preview
```

`--force` and `--session-id` overlap: `--session-id` already implies force, so
you don't need to pass both.

## All flags

```
--projects-dir PATH   Default: ~/.claude/projects
--dest-dir PATH       Default: ~/development/my-repos/knowledge-base-private/claude-sessions
--state-file PATH     Default: ~/.claude/session-export-state.json
--filter SUBSTRING    Match against project label/slug, session id, ai-title,
                      custom-title, or first user message
--session-id ID       Export exactly one session (exact match or unambiguous
                      prefix); implies --force
--list                List all discovered sessions as TAB-separated rows and
                      exit; honours --filter
--dry-run             Show the table; do not write or commit anything
--force               Re-export every (filtered) session regardless of state/mtime
--commit              git-commit the new transcripts in knowledge-base-private after export
-h, --help            Show help and exit
```

## State file

Lives at `~/.claude/session-export-state.json` by default — outside any git
repo, so it's never accidentally committed.

The JSON is keyed by the **original source jsonl path**:

```json
{
  "version": 1,
  "entries": {
    "/Users/.../.claude/projects/<proj>/<session-id>.jsonl": {
      "exported_at":   "2026-06-17T15:25:30",
      "source_mtime":  1781559704.44,
      "md_path":       "/Users/.../claude-sessions/<proj>/<short-name>.md",
      "jsonl_path":    "/Users/.../claude-sessions/<proj>/<short-name>.jsonl",
      "lines":         296,
      "project_label": "/Users/.../cloudera/cde/dex"
    }
  }
}
```

A session is "unexported" when its source path is missing from `entries` or
its current mtime is newer than the recorded `source_mtime`.

## Naming scheme

`<YYYY-MM-DD>-<slug>--<id8>`

- **date** — earliest jsonl timestamp (falls back to source mtime)
- **slug** — the latest `custom-title` if present, else `ai-title`, else the
  first user message → ASCII lowercase kebab-case, trimmed at a word
  boundary, max 60 chars
- **id8** — first 8 hex chars of the session UUID (collision-proof and
  links the file back to the original UUID-named source)

Examples:
- `2026-06-15-threat-modeling-for-livy-at-line-342--b091f3bd.md`
- `2026-06-13-hello--7ebea35a.md`
- `2026-07-16-dex-21945-spark-shs-tm-phase1-20260716-20260717--57bc07c7.md`

If a previous run used a different short name for a session (e.g. because the
title precedence rules changed, or the older raw-UUID scheme was in use), the
next run detects the mismatch and renames the existing exports in place — no
manual cleanup needed.

## Companion tool: session_rename_report.py

`session_rename_report.py` (same directory) previews *which* short-names would
change if you re-exported now, cross-referencing the state file against what
each session's jsonl currently says.

```bash
# Preview against the live state file
python3 ~/development/my-repos/linux-env/scripts/python/session_rename_report.py

# Or against a pre-change snapshot (useful when investigating a rename after
# already running --force)
cp ~/.claude/session-export-state.json /tmp/state-before.json
# ... make some change to the exporter's metadata reader ...
python3 ~/development/my-repos/linux-env/scripts/python/session_rename_report.py --state /tmp/state-before.json
```

Output is TAB-separated with columns `status`, `session_id`, `kind` (`md` /
`jsonl`), `old_path`, `new_path`, `md5_old`, `md5_new`, `cleanup_cmd`. Status
values:

- `old-only` — only the old-named file is on disk; rename hasn't happened yet
- `renamed` — only the new-named file is on disk; exporter already moved it
- `both-exist` — both present; `cleanup_cmd` removes the stale old one
- `missing` — neither present
