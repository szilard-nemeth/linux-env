#!/usr/bin/env python3
"""Export Claude Code session transcripts to a knowledge-base repo.

Walks ~/.claude/projects/<project-slug>/<session-id>.jsonl, exports each
unexported (or stale) session as both a rendered .md and a raw .jsonl into
~/development/my-repos/knowledge-base-private/claude-sessions/<project>/, and
tracks state in linux-env/config/claude-session-export-state.json so we only
re-export when the source mtime moves forward.

Usage:
    python export_claude_sessions.py [--dry-run] [--commit] [--filter SUBSTR]
    python export_claude_sessions.py --list [--filter SUBSTR] [--sort ORDER]
    python export_claude_sessions.py --session-id <ID> [--commit]

Table + --list output is sorted newest-first by default. Override with
--sort {mtime|mtime-asc|project|id|name}.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import click
from rich.console import Console
from rich.table import Table


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

HOME = Path.home()
DEFAULT_PROJECTS_DIR = HOME / ".claude" / "projects"
DEFAULT_KB_REPO = HOME / "development" / "my-repos" / "knowledge-base-private"
DEFAULT_DEST_DIR = DEFAULT_KB_REPO / "claude-sessions"
DEFAULT_STATE_FILE = HOME / ".claude" / "session-export-state.json"

STATE_VERSION = 1

# jsonl line types we don't render in the markdown body
NOISE_TYPES = {
    "mode",
    "permission-mode",
    "file-history-snapshot",
    "attachment",
    "last-prompt",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Session:
    project_slug: str  # raw dir name, e.g. "-Users-snemeth-development-..."
    project_label: str  # decoded for display, e.g. "/Users/snemeth/development/..."
    session_id: str
    source_path: Path
    source_mtime: float
    line_count: int
    ai_title: Optional[str] = None
    first_user_text: Optional[str] = None
    earliest_ts: Optional[str] = None  # ISO8601 string from jsonl
    latest_ts: Optional[str] = None  # ISO8601 string of the last message in the jsonl

    @property
    def short_name(self) -> str:
        """Deterministic, readable filename stem: <YYYY-MM-DD>-<slug>--<id8>."""
        date_part = (self.earliest_ts or "")[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_part):
            # Fall back to source mtime when no jsonl timestamp is available.
            date_part = _dt.datetime.fromtimestamp(self.source_mtime).strftime("%Y-%m-%d")
        title = self.ai_title or self.first_user_text or self.session_id
        slug = _slugify(title, max_len=60) or self.session_id[:8]
        return f"{date_part}-{slug}--{self.session_id[:8]}"

    @property
    def md_dest(self) -> Path:
        return Path(self.project_slug) / f"{self.short_name}.md"

    @property
    def jsonl_dest(self) -> Path:
        return Path(self.project_slug) / f"{self.short_name}.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def decode_project_slug(slug: str) -> str:
    """`-Users-snemeth-foo` -> `/Users/snemeth/foo` (display only)."""
    return slug.replace("-", "/")


_SLUG_BAD = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, max_len: int = 60) -> str:
    """Lower-kebab-case, ASCII-only, trimmed at word boundary when possible."""
    s = (text or "").lower().strip()
    s = _SLUG_BAD.sub("-", s).strip("-")
    if len(s) <= max_len:
        return s
    cut = s[:max_len]
    # Trim trailing partial word so the slug ends cleanly.
    if "-" in cut:
        cut = cut.rsplit("-", 1)[0]
    return cut.strip("-")


def _extract_user_text(rec: dict) -> Optional[str]:
    """Pull the first-real-user-text out of a `type: user` record, or None.

    Filters out tool-result-only entries (`<tool_use_result…>`) and command
    stubs (`[Request interrupted…]`) that shouldn't be used as a title
    fallback.
    """
    msg = rec.get("message", {})
    content = msg.get("content") if isinstance(msg, dict) else msg
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                break
    text = text.strip()
    if not text or text.startswith("<") or text.startswith("[Request interrupted"):
        return None
    return text[:200]


def _scan_session_metadata(jsonl_path: Path) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], int]:
    """Return (title, first_user_text, earliest_ts, latest_ts, line_count) for a session jsonl.

    Title precedence: the LATEST `custom-title` (user-set, e.g. via `/title`) wins
    over any `ai-title` (auto-generated). A session can have both; renames produce
    multiple `custom-title` records and we want the freshest one. `ai-title` is
    stable across the session so we take the first we see.
    """
    ai_title: Optional[str] = None
    custom_title: Optional[str] = None  # latest wins — renames overwrite
    first_user_text: Optional[str] = None
    earliest_ts: Optional[str] = None
    latest_ts: Optional[str] = None
    line_count = 0
    try:
        with jsonl_path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line_count += 1
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                rtype = rec.get("type")
                if rtype == "ai-title" and ai_title is None:
                    ai_title = rec.get("aiTitle") or rec.get("title")
                elif rtype == "custom-title":
                    ct = rec.get("customTitle") or rec.get("title")
                    if ct:
                        custom_title = ct  # keep overwriting → latest wins
                ts = rec.get("timestamp")
                if ts:
                    if earliest_ts is None or ts < earliest_ts:
                        earliest_ts = ts
                    if latest_ts is None or ts > latest_ts:
                        latest_ts = ts
                if rtype == "user" and first_user_text is None:
                    first_user_text = _extract_user_text(rec)
    except OSError:
        pass
    # Custom title wins over ai-title. Callers use this as `ai_title` — keeping
    # the field name for backward compat, but semantically it's "the best title
    # we could find" (user-set > AI-generated).
    return custom_title or ai_title, first_user_text, earliest_ts, latest_ts, line_count


def _load_uuid_pairs(jsonl_path: Path) -> tuple[set[str], set[str]]:
    """Return (record_uuids, parent_uuids) for every record in a session jsonl.

    Used only for fork detection on same-day same-slug sibling sessions — we
    don't call this on every session because it re-reads the file.
    """
    uuids: set[str] = set()
    parents: set[str] = set()
    try:
        with jsonl_path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                u = rec.get("uuid")
                if u:
                    uuids.add(u)
                p = rec.get("parentUuid")
                if p:
                    parents.add(p)
    except OSError:
        pass
    return uuids, parents


def _detect_forks(sessions: list[Session]) -> dict[str, Optional[str]]:
    """Return {session_id: parent_session_id_or_None} for likely-sibling sessions.

    Claude Code creates a fork when a session is resumed/rewound — a new
    session_id is allocated and prior transcript records are copied forward,
    keeping their original `uuid`s. We detect that by looking for pairs where
    the majority of one file's `parentUuid`s appear as `uuid`s in the other.
    Cost is bounded to the number of same-day-same-slug siblings per project,
    which is almost always 0 — we only pay the extra read when there's a
    genuine ambiguity to resolve.
    """
    forks: dict[str, Optional[str]] = {s.session_id: None for s in sessions}

    groups: dict[tuple[str, str], list[Session]] = {}
    for s in sessions:
        # Group by project + short_name prefix (everything before the `--<id8>`
        # suffix) so we compare true siblings — sessions whose `<date>-<slug>`
        # would collide are exactly the ones the user can't tell apart without
        # this metadata. Splitting on `--` isolates that prefix cheaply.
        prefix = s.short_name.rsplit("--", 1)[0]
        key = (s.project_slug, prefix)
        groups.setdefault(key, []).append(s)

    for group in groups.values():
        if len(group) < 2:
            continue
        loaded: dict[str, tuple[set[str], set[str]]] = {}
        for s in group:
            loaded[s.session_id] = _load_uuid_pairs(s.source_path)
        # For each ordered pair (a, b), check whether b looks like a fork of a.
        for b in group:
            b_uuids, b_parents = loaded[b.session_id]
            if not b_parents:
                continue
            best_parent: Optional[str] = None
            best_score = 0.0
            for a in group:
                if a.session_id == b.session_id:
                    continue
                a_uuids, _ = loaded[a.session_id]
                if not a_uuids:
                    continue
                overlap = len(b_parents & a_uuids)
                score = overlap / max(1, len(b_parents))
                # Require a majority of b's parent-uuids to live in a; ties
                # broken toward the *larger* candidate (the longer/surviving
                # branch is the parent).
                if score > 0.5 and (
                    score > best_score
                    or (score == best_score and best_parent is not None
                        and len(loaded[a.session_id][0]) > len(loaded[best_parent][0]))
                ):
                    best_parent = a.session_id
                    best_score = score
            if best_parent:
                forks[b.session_id] = best_parent
        # If detection made everyone a child of everyone else (rare — happens
        # when two forks are near-identical), keep only the newest as child
        # and clear the rest so the index shows one clear parent.
        children = [s.session_id for s in group if forks[s.session_id] in {x.session_id for x in group}]
        if len(children) == len(group):
            newest = max(group, key=lambda s: s.latest_ts or s.earliest_ts or "")
            for s in group:
                if s.session_id != newest.session_id:
                    forks[s.session_id] = newest.session_id
                else:
                    forks[s.session_id] = None
    return forks


def discover_sessions(projects_dir: Path) -> list[Session]:
    sessions: list[Session] = []
    if not projects_dir.exists():
        return sessions
    for proj in sorted(projects_dir.iterdir()):
        if not proj.is_dir():
            continue
        for jf in sorted(proj.glob("*.jsonl")):
            try:
                stat = jf.stat()
            except OSError:
                continue
            ai_title, first_user, earliest_ts, latest_ts, line_count = _scan_session_metadata(jf)
            sessions.append(
                Session(
                    project_slug=proj.name,
                    project_label=decode_project_slug(proj.name),
                    session_id=jf.stem,
                    source_path=jf,
                    source_mtime=stat.st_mtime,
                    line_count=line_count,
                    ai_title=ai_title,
                    first_user_text=first_user,
                    earliest_ts=earliest_ts,
                    latest_ts=latest_ts,
                )
            )
    return sessions


def load_state(path: Path) -> dict:
    """Load the export state file.

    Schema (also see the write site in main()):

        {
          "version": 1,
          "entries": {
            # KEY = the original source jsonl path verbatim. This is how we
            # remember the "real" filename of each session even though the
            # exported copies live under a renamed short name.
            "/Users/.../.claude/projects/<proj>/<session-id>.jsonl": {
              "exported_at":   "<ISO8601>",                 # when we wrote it
              "source_mtime":  <float>,                     # source mtime at export time
              "md_path":       "<abs path to .md export>",  # renamed short-name copy
              "jsonl_path":    "<abs path to .jsonl copy>", # renamed short-name copy
              "lines":         <int>,                       # source line count at export time
              "project_label": "<decoded project path>"
            },
            ...
          }
        }

    A session is considered "unexported" when its source path is missing from
    `entries`, or its current mtime is newer than the recorded `source_mtime`.
    """
    if not path.exists():
        return {"version": STATE_VERSION, "entries": {}}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"version": STATE_VERSION, "entries": {}}
    data.setdefault("version", STATE_VERSION)
    data.setdefault("entries", {})
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(path)


def export_status(session: Session, state: dict) -> str:
    """Returns 'fresh', 'stale', or 'never'."""
    entry = state["entries"].get(str(session.source_path))
    if not entry:
        return "never"
    prev_mtime = float(entry.get("source_mtime", 0))
    # Allow a tiny epsilon; mtime can wobble at FS resolution.
    if session.source_mtime > prev_mtime + 1e-6:
        return "stale"
    return "fresh"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _flatten_text(content) -> str:
    """Anthropic message content can be a str or a list of typed blocks."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                chunks.append(str(block))
                continue
            btype = block.get("type")
            if btype == "text":
                chunks.append(block.get("text", ""))
            elif btype == "tool_use":
                name = block.get("name", "?")
                inp = block.get("input", {})
                chunks.append(
                    f"\n**[tool_use: {name}]**\n```json\n"
                    f"{json.dumps(inp, indent=2, ensure_ascii=False)[:4000]}\n```"
                )
            elif btype == "tool_result":
                inner = block.get("content", "")
                inner_text = _flatten_text(inner)
                chunks.append(f"\n**[tool_result]**\n```\n{inner_text[:4000]}\n```")
            elif btype == "thinking":
                chunks.append(f"\n<details><summary>thinking</summary>\n\n{block.get('thinking', '')}\n\n</details>")
            else:
                chunks.append(f"\n[{btype}]")
        return "\n".join(chunks)
    return str(content)


def render_markdown(session: Session) -> str:
    out: list[str] = []
    out.append(f"# Claude session `{session.session_id}`")
    out.append("")
    out.append(f"- **Project:** `{session.project_label}`")
    out.append(f"- **Source:** `{session.source_path}`")
    out.append(f"- **Source mtime:** {_dt.datetime.fromtimestamp(session.source_mtime).isoformat(timespec='seconds')}")
    out.append(f"- **Total lines:** {session.line_count}")
    out.append("")
    out.append("---")
    out.append("")

    rendered_msgs = 0
    skipped = 0
    with session.source_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                skipped += 1
                continue
            rtype = rec.get("type")
            if rtype in NOISE_TYPES:
                skipped += 1
                continue
            if rtype in ("user", "assistant"):
                ts = rec.get("timestamp", "")
                msg = rec.get("message", {})
                content = msg.get("content") if isinstance(msg, dict) else msg
                text = _flatten_text(content)
                if not text.strip():
                    skipped += 1
                    continue
                out.append(f"## {rtype} — {ts}")
                out.append("")
                out.append(text)
                out.append("")
                rendered_msgs += 1
            elif rtype == "system":
                # Inline system notes briefly — they're useful context.
                content = rec.get("content") or rec.get("subtype") or ""
                if content:
                    out.append(f"> _system: {str(content)[:500]}_")
                    out.append("")
                    rendered_msgs += 1
            else:
                skipped += 1

    out.append("---")
    out.append("")
    out.append(f"_Rendered {rendered_msgs} messages; skipped {skipped} non-message lines._")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _parse_iso_ts(ts: Optional[str]) -> Optional[float]:
    """Parse an ISO8601 timestamp from the jsonl into a POSIX float, or None.

    Claude Code writes timestamps like "2026-08-01T05:17:30.811Z"; we normalise
    the trailing "Z" to a "+00:00" offset so `fromisoformat` accepts it on 3.9+.
    """
    if not ts:
        return None
    try:
        return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def export_session(session: Session, dest_dir: Path) -> tuple[Path, Path]:
    out_dir = dest_dir / session.project_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{session.short_name}.md"
    jsonl_path = out_dir / f"{session.short_name}.jsonl"
    md_path.write_text(render_markdown(session), encoding="utf-8")
    shutil.copy2(session.source_path, jsonl_path)
    # Stamp both exports with the session's last-message time so `ls -lt` in
    # the knowledge-base repo sorts by conversation recency, not export time.
    # If we can't parse a timestamp we leave mtime alone — `shutil.copy2`
    # already preserved the source's mtime on the jsonl copy.
    last_ts = _parse_iso_ts(session.latest_ts)
    if last_ts is not None:
        os.utime(md_path, (last_ts, last_ts))
        os.utime(jsonl_path, (last_ts, last_ts))
    return md_path, jsonl_path


def _print_session_list(sessions: list[Session], sort: str, console: Console) -> None:
    """Emit TAB-separated `session_id mtime lines name project_label` rows.

    `name` uses the same precedence as the short filename slug: AI-generated
    title (or user-set custom title if present), falling back to the first user
    message, falling back to `-`.
    """
    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return
    for s in sorted(sessions, key=_sort_key(sort)):
        name = s.ai_title or s.first_user_text or "-"
        name = name.replace("\t", " ").replace("\n", " ").strip()
        if len(name) > 120:
            name = name[:117] + "..."
        print(
            "\t".join(
                [
                    s.session_id,
                    _fmt_mtime(s.source_mtime),
                    str(s.line_count),
                    name,
                    s.project_label,
                ]
            )
        )


def _export_pending(
    pending: Iterable[Session],
    state: dict,
    dest_dir: Path,
    console: Console,
) -> list[Path]:
    """Export each pending session and update `state["entries"]` in place.

    The state-file entry is keyed by the ORIGINAL source jsonl path
    (e.g. `~/.claude/projects/<proj>/<session-id>.jsonl`). That key is the
    link between a session's source-of-truth and its renamed exports —
    `md_path` / `jsonl_path` record where the short-named copies live in
    knowledge-base-private. The file's basename is the raw session UUID, so
    the original "filename" is preserved both as the dict key and in the
    path itself.
    """
    written: list[Path] = []
    now_iso = _dt.datetime.now().isoformat(timespec="seconds")
    for s in pending:
        md_path, jsonl_path = export_session(s, dest_dir)
        state["entries"][str(s.source_path)] = {
            "exported_at": now_iso,
            "source_mtime": s.source_mtime,
            "md_path": str(md_path),
            "jsonl_path": str(jsonl_path),
            "lines": s.line_count,
            "project_label": s.project_label,
        }
        written.extend([md_path, jsonl_path])
        console.print(f"[green]exported[/green] {s.project_label} / {s.session_id}")
    return written


def _fmt_ts_short(ts: Optional[str]) -> str:
    """`2026-08-01T05:17:30.811Z` -> `2026-08-01 05:17`. Returns `—` on empty/parse fail."""
    if not ts:
        return "—"
    # ISO timestamps sort correctly as strings; cheap slice avoids parse cost.
    return ts[:16].replace("T", " ")


def write_project_indexes(
    sessions: Iterable[Session],
    state: dict,
    dest_dir: Path,
    forks: dict[str, Optional[str]],
) -> list[Path]:
    """Write `_INDEX.md` for every project directory that has exported sessions.

    Called unconditionally on non-dry-run invocations: the index is derived
    entirely from state + discovered sessions, so rebuilding is cheap and
    guarantees correctness even when a fork's sibling was exported in a prior
    run. Returns the list of index files written (so --commit picks them up).
    """
    by_project: dict[str, list[Session]] = {}
    for s in sessions:
        # Only include sessions that have actually been exported at least once —
        # unexported ones don't correspond to files on disk yet, and the index
        # is meant to describe the exported directory.
        if str(s.source_path) in state["entries"]:
            by_project.setdefault(s.project_slug, []).append(s)

    written: list[Path] = []
    now = _dt.datetime.now().replace(microsecond=0).isoformat()

    for project_slug, group in sorted(by_project.items()):
        # Newest-first by last message, falling back to earliest, then to the
        # source mtime so entries without any timestamps still get an order.
        group.sort(
            key=lambda s: (s.latest_ts or "", s.earliest_ts or "", s.source_mtime),
            reverse=True,
        )
        project_label = decode_project_slug(project_slug)
        lines = [
            f"# Claude sessions — `{project_label}`",
            "",
            f"_Updated {now}. Sorted newest-first by last message._",
            "",
            "| File | First msg | Last msg | Lines | Title | Fork of |",
            "|---|---|---|---|---|---|",
        ]
        for s in group:
            title = (s.ai_title or s.first_user_text or "").strip()
            # Collapse newlines/tabs so a table row stays a single markdown
            # row — first_user_text can be multi-line when it falls back from
            # a missing ai-title.
            title = re.sub(r"\s+", " ", title).replace("|", "\\|")
            if len(title) > 80:
                title = title[:77] + "..."
            if not title:
                title = "—"
            parent_id = forks.get(s.session_id)
            fork_cell = parent_id[:8] if parent_id else "—"
            md_name = f"{s.short_name}.md"
            lines.append(
                f"| [{md_name}]({md_name}) | {_fmt_ts_short(s.earliest_ts)} | "
                f"{_fmt_ts_short(s.latest_ts)} | {s.line_count} | {title} | {fork_cell} |"
            )
        lines.append("")

        out_path = dest_dir / project_slug / "_INDEX.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")
        written.append(out_path)

    return written


def migrate_existing_exports(
    sessions: Iterable[Session],
    state: dict,
    dest_dir: Path,
    console: Console,
    *,
    dry_run: bool,
) -> int:
    """Rename previously-exported `<session-id>.{md,jsonl}` to the new short name.

    Returns the number of sessions whose exports were renamed.
    """
    renamed = 0
    for s in sessions:
        entry = state["entries"].get(str(s.source_path))
        if not entry:
            continue
        old_md = Path(entry.get("md_path", ""))
        old_jsonl = Path(entry.get("jsonl_path", ""))
        new_md = dest_dir / s.md_dest
        new_jsonl = dest_dir / s.jsonl_dest
        moves: list[tuple[Path, Path]] = []
        if old_md and old_md != new_md and old_md.exists() and not new_md.exists():
            moves.append((old_md, new_md))
        if old_jsonl and old_jsonl != new_jsonl and old_jsonl.exists() and not new_jsonl.exists():
            moves.append((old_jsonl, new_jsonl))
        if not moves:
            continue
        if dry_run:
            for src, dst in moves:
                console.print(f"[cyan]would rename[/cyan] {src.name} -> {dst.name}")
        else:
            new_md.parent.mkdir(parents=True, exist_ok=True)
            for src, dst in moves:
                src.rename(dst)
                console.print(f"[cyan]renamed[/cyan] {src.name} -> {dst.name}")
            entry["md_path"] = str(new_md)
            entry["jsonl_path"] = str(new_jsonl)
        renamed += 1
    return renamed


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


STATUS_CELLS = {
    "fresh": ("✓", "green"),
    "stale": ("↻", "yellow"),
    "never": ("✗", "red"),
    "missing": ("?", "magenta"),
}


def _fmt_mtime(ts: float) -> str:
    return _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


# --- sort keys ---
# Choices are shared between the table renderer, --list output, and the CLI.
# `mtime` (newest-first) is the default — most workflows want "what did I
# touch recently?" over grouping by project.
SORT_CHOICES = ("mtime", "mtime-asc", "project", "id", "name")


def _sort_key(sort: str):
    """Return a key function suitable for `sorted(sessions, key=...)`."""
    if sort == "mtime":
        return lambda s: -s.source_mtime  # newest-first
    if sort == "mtime-asc":
        return lambda s: s.source_mtime
    if sort == "project":
        return lambda s: (s.project_label, s.source_mtime)
    if sort == "id":
        return lambda s: s.session_id
    if sort == "name":
        return lambda s: ((s.ai_title or s.first_user_text or "").lower(), s.source_mtime)
    raise ValueError(f"unknown sort: {sort}")


def _fmt_export_loc(entry: dict | None, dest_dir: Path, session: Session) -> str:
    if not entry:
        return "—"
    md = entry.get("md_path", "")
    if not md:
        return "—"
    try:
        return str(Path(md).relative_to(dest_dir.parent))
    except ValueError:
        return md


def render_table(
    sessions: Iterable[Session],
    state: dict,
    dest_dir: Path,
    title: str = "Claude session transcripts",
    sort: str = "mtime",
) -> Table:
    table = Table(title=title, show_lines=False, header_style="bold cyan")
    table.add_column("Project", overflow="fold", max_width=30)
    table.add_column("Session (short name)", overflow="fold", max_width=42)
    table.add_column("Source path", overflow="fold", max_width=50)
    table.add_column("State", justify="center")
    table.add_column("MTime")
    table.add_column("Last msg")
    table.add_column("Export location", overflow="fold", max_width=40)
    table.add_column("Lines", justify="right")

    for s in sorted(sessions, key=_sort_key(sort)):
        status = export_status(s, state)
        cell, colour = STATUS_CELLS[status]
        entry = state["entries"].get(str(s.source_path))
        table.add_row(
            s.project_label,
            s.short_name,
            str(s.source_path),
            f"[{colour}]{cell} {status}[/{colour}]",
            _fmt_mtime(s.source_mtime),
            _fmt_ts_short(s.latest_ts),
            _fmt_export_loc(entry, dest_dir, s),
            str(s.line_count),
        )
    return table


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _has_changes(repo: Path, paths: list[Path]) -> bool:
    rel = []
    for p in paths:
        try:
            rel.append(str(p.relative_to(repo)))
        except ValueError:
            continue
    if not rel:
        return False
    cp = subprocess.run(
        ["git", "status", "--porcelain", "--", *rel],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(cp.stdout.strip())


def commit_repo(repo: Path, paths: list[Path], message: str, console: Console) -> bool:
    if not _has_changes(repo, paths):
        console.print(f"[dim]{repo.name}: no changes to commit[/dim]")
        return False
    rel = [str(p.relative_to(repo)) for p in paths if p.is_relative_to(repo)]
    _git(repo, "add", "--", *rel)
    _git(repo, "commit", "-m", message)
    console.print(f"[green]{repo.name}: committed {len(rel)} path(s)[/green]")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--projects-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_PROJECTS_DIR,
    show_default=True,
    help="Root directory of Claude session projects.",
)
@click.option(
    "--dest-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_DEST_DIR,
    show_default=True,
    help="Where to write exported transcripts.",
)
@click.option(
    "--state-file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_STATE_FILE,
    show_default=True,
    help="JSON file tracking per-source export state.",
)
@click.option(
    "--filter",
    "filter_substr",
    default=None,
    help="Only consider sessions whose project label, session id, ai-title, "
    "or first-user-message contains this substring (case-insensitive).",
)
@click.option(
    "--session-id",
    "session_id",
    default=None,
    help="Export exactly one session by id (exact match, or unambiguous prefix). "
    "Errors out if 0 or >1 sessions match. Implies --force.",
)
@click.option(
    "--list",
    "list_sessions",
    is_flag=True,
    help="List every discovered session (id, name, project) and exit. "
    "Pipe-friendly: one TAB-separated row per session. Honours --filter and --sort.",
)
@click.option(
    "--sort",
    "sort",
    type=click.Choice(list(SORT_CHOICES), case_sensitive=False),
    default="mtime",
    show_default=True,
    help="Sort order for the table and --list output. 'mtime' is newest-first; "
    "'mtime-asc' is oldest-first; 'project' groups by project then mtime; "
    "'id' sorts by session UUID; 'name' sorts by title/first-user-message.",
)
@click.option("--dry-run", is_flag=True, help="Show the table; do not write or commit anything.")
@click.option(
    "--force",
    is_flag=True,
    help="Re-export every (filtered) session regardless of state/mtime. "
    "Useful when the markdown template changes or the dest dir was wiped.",
)
@click.option(
    "--commit",
    "do_commit",
    is_flag=True,
    help="After exporting, git-commit the new transcripts in the knowledge-base repo.",
)
def main(
    projects_dir: Path,
    dest_dir: Path,
    state_file: Path,
    filter_substr: str | None,
    session_id: str | None,
    list_sessions: bool,
    sort: str,
    dry_run: bool,
    force: bool,
    do_commit: bool,
) -> None:
    """Export unexported Claude session transcripts."""
    console = Console()

    # Keep the full unfiltered list around so `_INDEX.md` reflects every
    # exported session in each project, not just the subset the caller asked
    # to work on this run.
    all_sessions = discover_sessions(projects_dir)
    sessions = all_sessions
    if filter_substr:
        needle = filter_substr.lower()

        def _matches(s: Session) -> bool:
            haystacks = [
                s.project_label,
                s.project_slug,
                s.session_id,
                s.ai_title or "",
                s.first_user_text or "",
            ]
            return any(needle in h.lower() for h in haystacks)

        sessions = [s for s in sessions if _matches(s)]

    if list_sessions:
        _print_session_list(sessions, sort, console)
        return

    if session_id:
        needle = session_id.lower()
        exact = [s for s in sessions if s.session_id.lower() == needle]
        prefix = [s for s in sessions if s.session_id.lower().startswith(needle)]
        matches = exact if exact else prefix
        if not matches:
            console.print(f"[red]No session matches id '{session_id}'.[/red]")
            raise SystemExit(1)
        if len(matches) > 1:
            console.print(f"[red]Session id '{session_id}' is ambiguous — {len(matches)} matches:[/red]")
            for s in matches:
                console.print(f"  {s.session_id}  ({s.project_label})")
            raise SystemExit(1)
        sessions = matches
        force = True  # single-session exports are almost always "rewrite this now".

    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    state = load_state(state_file)

    # Migrate any pre-existing exports to the new <date>-<slug>--<id8> naming.
    migrated = migrate_existing_exports(sessions, state, dest_dir, console, dry_run=dry_run)
    if migrated and not dry_run:
        save_state(state_file, state)
        console.print(f"[cyan]Migrated {migrated} existing export(s) to short-name files.[/cyan]")

    if force:
        pending = list(sessions)
    else:
        pending = [s for s in sessions if export_status(s, state) in ("never", "stale")]

    console.print(render_table(sessions, state, dest_dir, title="Claude session transcripts (before)", sort=sort))
    if force:
        console.print(f"\n[bold]--force[/bold]: re-exporting all [bold]{len(pending)}[/bold] session(s).")
    else:
        console.print(f"\n[bold]{len(pending)}[/bold] of [bold]{len(sessions)}[/bold] sessions need export.")

    if dry_run:
        console.print("[dim]--dry-run: not writing anything.[/dim]")
        return

    if not pending:
        console.print("[green]Nothing to do.[/green]")
        return

    written_paths = _export_pending(pending, state, dest_dir, console)

    save_state(state_file, state)
    console.print(f"\n[bold]Exported {len(pending)} session(s).[/bold] State: {state_file}")

    # Rebuild `_INDEX.md` for every project (always) so the exported directory
    # shows conversation-recency, line counts, titles, and fork lineage without
    # needing the shell. Runs off `all_sessions` so untouched projects still
    # get a correct index when the user is exporting with --filter.
    forks = _detect_forks(all_sessions)
    index_paths = write_project_indexes(all_sessions, state, dest_dir, forks)
    if index_paths:
        console.print(f"[cyan]Wrote {len(index_paths)} _INDEX.md file(s).[/cyan]")
    written_paths.extend(index_paths)

    # Re-render after exports so the user sees the updated status column.
    console.print(render_table(sessions, state, dest_dir, title="Claude session transcripts (after)", sort=sort))

    if do_commit:
        today = _dt.date.today().isoformat()
        msg = f"Export {len(pending)} Claude session transcript(s) ({today})"

        # knowledge-base-private: the new transcripts.
        kb_repo = dest_dir
        # walk up to the repo root
        while kb_repo != kb_repo.parent and not (kb_repo / ".git").exists():
            kb_repo = kb_repo.parent
        if (kb_repo / ".git").exists():
            commit_repo(kb_repo, written_paths, msg, console)
        else:
            console.print(f"[yellow]Skip commit: {dest_dir} has no parent .git repo[/yellow]")


if __name__ == "__main__":
    main()
