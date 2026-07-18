#!/usr/bin/env python3
"""Preview short-name renames for exported Claude sessions.

Re-scans each session jsonl with the current metadata reader (custom-title
takes precedence over ai-title) and reports every exported file whose
short-name would change vs. what's recorded in the state file.

Typical workflow — using a snapshot taken BEFORE a fixing re-export:

    cp ~/.claude/session-export-state.json /tmp/state-before.json
    python session_rename_report.py --state /tmp/state-before.json

Or against the live state (useful when only the metadata reader changed but
you haven't re-exported yet):

    python session_rename_report.py

Columns (TAB-separated):
    status  session_id  kind  old_path  new_path  md5_old  md5_new  cleanup_cmd

status values:
    old-only    only the old-named file exists (rename hasn't run yet)
    renamed     only the new-named file exists (rename already happened)
    both-exist  both files present — cleanup_cmd removes the old one
    missing     neither file present
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Import the exporter's helpers directly so slug logic stays in one place.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from export_claude_sessions import (  # type: ignore
    DEFAULT_DEST_DIR,
    DEFAULT_STATE_FILE,
    Session,
    _scan_session_metadata,
    decode_project_slug,
)


def md5_of(path: Path) -> str:
    if not path.exists():
        return "-"
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def shquote(s: str) -> str:
    if not s or any(c in s for c in " \t'\"\\$`"):
        return "'" + s.replace("'", "'\\''") + "'"
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help=f"State file to read old export paths from (default: {DEFAULT_STATE_FILE}).",
    )
    ap.add_argument(
        "--dest-dir", type=Path, default=DEFAULT_DEST_DIR, help=f"Where exports live (default: {DEFAULT_DEST_DIR})."
    )
    args = ap.parse_args()

    state = json.loads(args.state.read_text())
    entries = state.get("entries", {})
    rows: list[tuple[str, str, str, str, str]] = []
    for src_path_str, entry in sorted(entries.items()):
        src = Path(src_path_str)
        if not src.exists():
            # Source jsonl was deleted; don't try to derive a new name for it.
            continue
        ai_title, first_user, earliest_ts, line_count = _scan_session_metadata(src)
        project_slug = src.parent.name
        s = Session(
            project_slug=project_slug,
            project_label=decode_project_slug(project_slug),
            session_id=src.stem,
            source_path=src,
            source_mtime=float(entry.get("source_mtime", src.stat().st_mtime)),
            line_count=line_count,
            ai_title=ai_title,
            first_user_text=first_user,
            earliest_ts=earliest_ts,
        )
        new_md = args.dest_dir / s.md_dest
        new_jsonl = args.dest_dir / s.jsonl_dest
        old_md = Path(entry.get("md_path") or "")
        old_jsonl = Path(entry.get("jsonl_path") or "")
        if old_md == new_md and old_jsonl == new_jsonl:
            continue  # no rename needed
        rows.append((s.session_id, str(old_md), str(new_md), str(old_jsonl), str(new_jsonl)))

    if not rows:
        print("No renames needed — every session's short-name matches the current metadata.")
        return 0

    print("\t".join(["status", "session_id", "kind", "old_path", "new_path", "md5_old", "md5_new", "cleanup_cmd"]))
    for session_id, old_md, new_md, old_jsonl, new_jsonl in rows:
        for kind, old, new in (("md", old_md, new_md), ("jsonl", old_jsonl, new_jsonl)):
            old_p = Path(old) if old else Path("/dev/null/never")
            new_p = Path(new)
            old_exists = bool(old) and old_p.exists() and old_p != new_p
            new_exists = new_p.exists()
            if old_exists and new_exists:
                status = "both-exist"
                cleanup = f"rm {shquote(old)}"
            elif old_exists and not new_exists:
                status = "old-only"
                cleanup = "# will be renamed by re-export"
            elif not old_exists and new_exists:
                status = "renamed"
                cleanup = "# nothing to clean"
            else:
                status = "missing"
                cleanup = "# neither file present"
            print(
                "\t".join(
                    [
                        status,
                        session_id[:8],
                        kind,
                        old,
                        new,
                        md5_of(old_p) if old else "-",
                        md5_of(new_p),
                        cleanup,
                    ]
                )
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
