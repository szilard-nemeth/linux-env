#!/usr/bin/env python3
"""Export Claude Code session transcripts to a knowledge-base repo.

Walks ~/.claude/projects/<project-slug>/<session-id>.jsonl, exports each
unexported (or stale) session as both a rendered .md and a raw .jsonl into
~/development/my-repos/knowledge-base-private/claude-sessions/<project>/, and
tracks state in linux-env/config/claude-session-export-state.json so we only
re-export when the source mtime moves forward.

Usage:
    python export_claude_sessions.py [--dry-run] [--commit] [--filter SUBSTR]
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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

    @property
    def md_dest(self) -> Path:
        return Path(self.project_slug) / f"{self.session_id}.md"

    @property
    def jsonl_dest(self) -> Path:
        return Path(self.project_slug) / f"{self.session_id}.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def decode_project_slug(slug: str) -> str:
    """`-Users-snemeth-foo` -> `/Users/snemeth/foo` (display only)."""
    return slug.replace("-", "/")


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
                # Cheap line count — these files aren't huge.
                with jf.open("rb") as fh:
                    line_count = sum(1 for _ in fh)
            except OSError:
                continue
            sessions.append(
                Session(
                    project_slug=proj.name,
                    project_label=decode_project_slug(proj.name),
                    session_id=jf.stem,
                    source_path=jf,
                    source_mtime=stat.st_mtime,
                    line_count=line_count,
                )
            )
    return sessions


def load_state(path: Path) -> dict:
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


def export_session(session: Session, dest_dir: Path) -> tuple[Path, Path]:
    out_dir = dest_dir / session.project_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{session.session_id}.md"
    jsonl_path = out_dir / f"{session.session_id}.jsonl"
    md_path.write_text(render_markdown(session), encoding="utf-8")
    shutil.copy2(session.source_path, jsonl_path)
    return md_path, jsonl_path


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
) -> Table:
    table = Table(title=title, show_lines=False, header_style="bold cyan")
    table.add_column("Project", overflow="fold", max_width=30)
    table.add_column("Session", overflow="fold")
    table.add_column("Source path", overflow="fold", max_width=50)
    table.add_column("State", justify="center")
    table.add_column("MTime")
    table.add_column("Export location", overflow="fold", max_width=40)
    table.add_column("Lines", justify="right")

    for s in sorted(sessions, key=lambda x: (x.project_label, x.source_mtime)):
        status = export_status(s, state)
        cell, colour = STATUS_CELLS[status]
        entry = state["entries"].get(str(s.source_path))
        table.add_row(
            s.project_label,
            s.session_id,
            str(s.source_path),
            f"[{colour}]{cell} {status}[/{colour}]",
            _fmt_mtime(s.source_mtime),
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
    help="Only consider sessions whose project label or session id contains this substring.",
)
@click.option("--dry-run", is_flag=True, help="Show the table; do not write or commit anything.")
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
    dry_run: bool,
    do_commit: bool,
) -> None:
    """Export unexported Claude session transcripts."""
    console = Console()

    sessions = discover_sessions(projects_dir)
    if filter_substr:
        needle = filter_substr.lower()
        sessions = [
            s
            for s in sessions
            if needle in s.project_label.lower() or needle in s.project_slug.lower() or needle in s.session_id.lower()
        ]

    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    state = load_state(state_file)

    pending = [s for s in sessions if export_status(s, state) in ("never", "stale")]

    console.print(render_table(sessions, state, dest_dir, title="Claude session transcripts (before)"))
    console.print(f"\n[bold]{len(pending)}[/bold] of [bold]{len(sessions)}[/bold] sessions need export.")

    if dry_run:
        console.print("[dim]--dry-run: not writing anything.[/dim]")
        return

    if not pending:
        console.print("[green]Nothing to do.[/green]")
        return

    written_paths: list[Path] = []
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
        written_paths.extend([md_path, jsonl_path])
        console.print(f"[green]exported[/green] {s.project_label} / {s.session_id}")

    save_state(state_file, state)
    console.print(f"\n[bold]Exported {len(pending)} session(s).[/bold] State: {state_file}")

    # Re-render after exports so the user sees the updated status column.
    console.print(render_table(sessions, state, dest_dir, title="Claude session transcripts (after)"))

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
