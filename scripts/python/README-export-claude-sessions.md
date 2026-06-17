# export_claude_sessions.py

Click-based CLI that incrementally exports Claude Code session transcripts
(`~/.claude/projects/<proj>/<session-id>.jsonl`) into the
`knowledge-base-private` repo as readable Markdown plus the raw `.jsonl`,
tracking what's been exported in a JSON state file so re-runs only copy what
changed.

## Quick start

```bash
# Inspect the current state without changing anything
python3 scripts/python/export_claude_sessions.py --dry-run

# Export everything that's new or changed
python3 scripts/python/export_claude_sessions.py

# Export and git-commit the new transcripts
python3 scripts/python/export_claude_sessions.py --commit
```

## What it does

1. Walks `~/.claude/projects/*/*.jsonl`.
2. For each session, reads the jsonl once to extract:
   - `aiTitle` (Claude Code's auto-generated session title) — used for slug
   - first user prompt (fallback when no `aiTitle`)
   - earliest timestamp (used for the date prefix)
   - line count
3. Compares `source_mtime` against the recorded `source_mtime` in the state
   file. New or changed sessions are flagged for export.
4. Writes both `.md` (rendered transcript) and `.jsonl` (raw copy) into
   `~/development/my-repos/knowledge-base-private/claude-sessions/<project-slug>/`
   under the **deterministic short name**
   `<YYYY-MM-DD>-<slug>--<id8>` — e.g.
   `2026-06-15-threat-modeling-for-livy-at-line-342--b091f3bd.md`.
5. Updates the state file.
6. Optionally commits the new transcripts to `knowledge-base-private`.

## Just want to see the state?

Yes — `--dry-run` prints the full status table and writes nothing:

```bash
python3 scripts/python/export_claude_sessions.py --dry-run
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

## Filter to a subset

```bash
# Only sessions whose project label, project slug, or session id contains 'livy'
python3 scripts/python/export_claude_sessions.py --dry-run --filter livy
```

## Force a full re-export

Useful after editing the markdown template or wiping the destination:

```bash
python3 scripts/python/export_claude_sessions.py --force
python3 scripts/python/export_claude_sessions.py --force --filter linux-env  # subset
python3 scripts/python/export_claude_sessions.py --force --dry-run           # preview
```

## All flags

```
--projects-dir PATH   Default: ~/.claude/projects
--dest-dir PATH       Default: ~/development/my-repos/knowledge-base-private/claude-sessions
--state-file PATH     Default: ~/.claude/session-export-state.json
--filter SUBSTRING    Match against project label, project slug, or session id
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
- **slug** — `aiTitle` (or first user prompt) → ASCII lowercase kebab-case,
  trimmed at a word boundary, max 60 chars
- **id8** — first 8 hex chars of the session UUID (collision-proof and
  links the file back to the original UUID-named source)

Examples:
- `2026-06-15-threat-modeling-for-livy-at-line-342--b091f3bd.md`
- `2026-06-13-hello--7ebea35a.md`
- `2026-06-17-build-cli-script-for-exporting-session-transcripts--a7b89284.md`

If a previous run used the older raw-UUID filename scheme, the next run
detects the mismatch and renames the existing exports in place — no manual
cleanup needed.
