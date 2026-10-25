#!/usr/bin/env python3
"""Snapshot the text of every kitty window into per-window files.

Companion to kitty_save_session.py. The session file restores *layout*;
this script captures *what was on screen* -- one text file per window,
plus an index.md that summarises tab titles, cwds, and running processes.
Use this as a visual/memory aid so you can see roughly what each tab was
doing, even for state that a restart cannot recreate (unsaved buffers,
REPL contents, tail output, error messages you meant to read).

Uses `kitty @ get-text` under the hood. Default extent is `screen`
(what is visible right now, i.e. the "screenshot" equivalent). Pass
--scrollback to grab the full scrollback buffer as well.

By default files are ANSI-coloured -- `cat` them in a terminal to see
the original colours. Pass --plain for stripped text (better for grep).

Output layout:
    <outdir>/
        index.md                              # human-readable overview
        os1-tab01-work-win1.ansi              # one file per kitty window
        os1-tab02-logs-win1.ansi
        os1-tab02-logs-win2.ansi

An `outdir` of `auto` (default) creates a timestamped directory under
~/.config/kitty/snapshots/ and updates the `latest` symlink to point at
it, so `less ~/.config/kitty/snapshots/latest/index.md` always shows
the most recent snapshot.

Retention: snapshots under the default root are pruned by age
(--prune-days) and by a total size ceiling (--max-bytes), oldest first.
The newest snapshot is never pruned, whatever its age. Pruning only ever
touches timestamped directories under the default root.

Usage:
    kitty_snapshot_windows.py
    kitty_snapshot_windows.py --scrollback           # include scrollback
    kitty_snapshot_windows.py --plain                # strip ANSI escapes
    kitty_snapshot_windows.py -o /tmp/before-reboot  # explicit dir
    kitty_snapshot_windows.py --prune-only           # just enforce retention
"""

from __future__ import annotations

import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

# See the note in kitty_save_session.py: keeps __pycache__ out of
# ~/.linuxenv/scripts/kitty, which remove-stale-scripts would churn.
sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import kitty_session_lib as ksl  # noqa: E402

DEFAULT_ROOT = ksl.SNAPSHOT_ROOT

# Snapshot dirs are named by resolve_outdir(); pruning only considers names
# matching this shape, so an unrelated directory dropped in the root is safe.
_STAMP_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")

DEFAULT_PRUNE_DAYS = 7
DEFAULT_MAX_BYTES = 2 * 1024**3  # 2 GiB


def die(msg: str) -> "None":
    ksl.die(msg)


def get_text(window_id: int, extent: str, ansi: bool, to: str | None = None) -> str:
    """Return the text of a window via `kitty @ get-text`."""
    args = ["get-text", "--match", f"id:{window_id}", "--extent", extent]
    if ansi:
        args.append("--ansi")
    proc = ksl.kitty_remote(args, to=to)
    if proc.returncode != 0:
        return f"[error: get-text failed for id:{window_id}: {proc.stderr.strip()}]\n"
    return proc.stdout


_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def slugify(text: str, maxlen: int = 40) -> str:
    """Turn a title into something safe for a filename."""
    if not text:
        return ""
    s = _SAFE_RE.sub("_", text.strip()).strip("_")
    return s[:maxlen] or ""


def foreground_summary(window: dict) -> str:
    """Compact one-line description of what is running in this window."""
    procs = window.get("foreground_processes") or []
    if not procs:
        return "(no foreground process)"
    parts = []
    for p in procs:
        cmdline = p.get("cmdline") or []
        if not cmdline:
            continue
        parts.append(" ".join(cmdline))
    return " | ".join(parts) if parts else "(no cmdline)"


def resolve_outdir(arg_value: str) -> Path:
    if arg_value == "auto":
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return DEFAULT_ROOT / stamp
    return Path(arg_value).expanduser()


def update_latest_symlink(outdir: Path) -> None:
    """Point ~/.config/kitty/snapshots/latest at the just-written dir."""
    try:
        parent = outdir.parent
        if parent != DEFAULT_ROOT:
            return  # only manage the symlink under our default root
        link = parent / "latest"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(outdir.name)  # relative target keeps it portable
    except OSError as e:
        print(f"warn: could not update `latest` symlink: {e}", file=sys.stderr)


def snapshot_dirs() -> list[Path]:
    """Timestamped snapshot dirs under the default root, newest first."""
    if not DEFAULT_ROOT.is_dir():
        return []
    dirs = [p for p in DEFAULT_ROOT.iterdir() if p.is_dir() and not p.is_symlink() and _STAMP_DIR_RE.match(p.name)]
    return sorted(dirs, key=lambda p: p.name, reverse=True)


def prune_snapshots(
    prune_days: int = DEFAULT_PRUNE_DAYS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    quiet: bool = False,
) -> int:
    """Enforce retention under the default root. Returns dirs removed.

    Two independent limits, applied oldest-first: anything older than
    `prune_days`, then whatever else is needed to get total size under
    `max_bytes`. The newest snapshot is always kept -- losing the most recent
    capture to a retention rule would defeat the point of taking it.
    """
    dirs = snapshot_dirs()
    if len(dirs) <= 1:
        return 0

    prunable = dirs[1:]  # never the newest
    removed = 0

    if prune_days > 0:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=prune_days)
        for path in list(prunable):
            try:
                when = datetime.datetime.strptime(path.name, "%Y-%m-%d_%H-%M-%S")
            except ValueError:
                continue
            if when < cutoff:
                if _remove_dir(path, "age", quiet):
                    removed += 1
                    prunable.remove(path)

    if max_bytes > 0:
        total = ksl.dir_size(DEFAULT_ROOT)
        # Oldest first.
        for path in sorted(prunable, key=lambda p: p.name):
            if total <= max_bytes:
                break
            size = ksl.dir_size(path)
            if _remove_dir(path, "size cap", quiet):
                removed += 1
                total -= size

    return removed


def _remove_dir(path: Path, reason: str, quiet: bool) -> bool:
    # Belt and braces: never delete outside the default root.
    if path.parent != DEFAULT_ROOT or not _STAMP_DIR_RE.match(path.name):
        return False
    try:
        shutil.rmtree(path)
    except OSError as e:
        print(f"warn: could not prune {path}: {e}", file=sys.stderr)
        return False
    if not quiet:
        print(f"pruned ({reason}): {path.name}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--outdir",
        default="auto",
        help=(
            "Output directory. Default 'auto' creates a timestamped subdir "
            f"under {DEFAULT_ROOT} and updates the 'latest' symlink."
        ),
    )
    parser.add_argument(
        "--scrollback",
        action="store_true",
        help="Capture screen + full scrollback (default: visible screen only)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Strip ANSI colour escapes (default: keep them; `cat` shows colours)",
    )
    parser.add_argument(
        "--to",
        metavar="ADDRESS",
        help=(
            "kitty remote-control address, e.g. unix:/path/to/kitty.sock-123. "
            "Default: the ambient instance, falling back to live sockets."
        ),
    )
    parser.add_argument(
        "--prune-days",
        type=int,
        default=DEFAULT_PRUNE_DAYS,
        help=f"Delete snapshots older than N days (0 disables; default: {DEFAULT_PRUNE_DAYS})",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"Total size ceiling for all snapshots (0 disables; default: {DEFAULT_MAX_BYTES})",
    )
    parser.add_argument(
        "--no-prune",
        action="store_true",
        help="Skip retention enforcement entirely for this run",
    )
    parser.add_argument(
        "--prune-only",
        action="store_true",
        help="Only enforce retention; do not capture a new snapshot",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Do not print the summary after writing",
    )
    args = parser.parse_args()

    if args.prune_only:
        removed = prune_snapshots(args.prune_days, args.max_bytes, args.quiet)
        if not args.quiet:
            print(f"OK: pruned {removed} snapshot dir(s); total now {ksl.human_bytes(ksl.dir_size(DEFAULT_ROOT))}")
        return 0

    data = ksl.collect_layout(to=args.to)
    if not data:
        die(f"`kitty @ ls` returned no windows -- {ksl.unreachable_hint()}")

    outdir = resolve_outdir(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    extent = "all" if args.scrollback else "screen"
    ansi = not args.plain
    ext = "txt" if args.plain else "ansi"

    index_lines: list[str] = []
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    index_lines.append(f"# kitty snapshot -- {stamp}")
    index_lines.append("")
    index_lines.append(f"extent: `{extent}`  |  colours: {'ANSI kept' if ansi else 'stripped'}")
    index_lines.append("")

    file_count = 0
    for os_idx, osw in enumerate(data, start=1):
        index_lines.append(f"## OS window {os_idx}")
        index_lines.append("")
        for t_idx, tab in enumerate(osw.get("tabs", []), start=1):
            tab_title = (tab.get("title") or "").strip()
            layout = tab.get("layout") or ""
            title_slug = slugify(tab_title)
            header = f"### Tab {t_idx}"
            if tab_title:
                header += f' -- "{tab_title}"'
            if layout:
                header += f"  _(layout: {layout})_"
            if tab.get("is_focused"):
                header += "  __(focused)__"
            index_lines.append(header)

            windows = tab.get("windows", []) or []
            for w_idx, w in enumerate(windows, start=1):
                wid = w.get("id")
                cwd = w.get("cwd") or ""
                fg = foreground_summary(w)
                fname = f"os{os_idx}-tab{t_idx:02d}" + (f"-{title_slug}" if title_slug else "") + f"-win{w_idx}.{ext}"
                path = outdir / fname
                text = get_text(wid, extent=extent, ansi=ansi, to=args.to)
                path.write_text(text)
                file_count += 1

                bullet = f"- **win{w_idx}**"
                if w.get("is_focused"):
                    bullet += " __(focused)__"
                if cwd:
                    bullet += f" cwd `{cwd}`"
                bullet += f" -- running: `{fg}`"
                bullet += f"  ->  [{fname}]({fname})"
                index_lines.append(bullet)
            index_lines.append("")

    (outdir / "index.md").write_text("\n".join(index_lines).rstrip() + "\n")

    if args.outdir == "auto":
        update_latest_symlink(outdir)
        if not args.no_prune:
            prune_snapshots(args.prune_days, args.max_bytes, args.quiet)

    if not args.quiet:
        print(f"OK: wrote {file_count} window file(s) to {outdir}")
        print(f"index: {outdir / 'index.md'}")
        if args.outdir == "auto":
            print(f"latest: {DEFAULT_ROOT / 'latest'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
