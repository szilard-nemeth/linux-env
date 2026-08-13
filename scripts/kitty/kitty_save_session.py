#!/usr/bin/env python3
"""Snapshot the current kitty layout to a session file for later restore.

Queries the running kitty via `kitty @ ls`, then writes a session file with
one entry per OS window / tab / window (all tabs, their titles, layouts,
working directories, and -- by default -- the currently-running foreground
command in each window). Restore with:

    kitty --session <file>

or set `startup_session <file>` in kitty.conf so it happens on launch.

Requires `allow_remote_control yes` in kitty.conf.

Foreground-command capture (--restore-processes, default on):
    - If a window is at an idle shell prompt, only shell+cwd is restored.
    - If a window is running a non-shell process (nvim, less, tail, python,
      ssh, ...), that exact argv is re-launched on restore, with its cwd.
    - In-memory state is NOT preserved: nvim reopens the same file(s) but
      loses unsaved buffers, jump history, and undo tree; less reopens the
      file at the top; REPLs restart empty. Save unsaved work before
      relying on this.
    - Non-idempotent commands are re-run verbatim on restore. Be careful
      with things like `docker run`, `kubectl apply`, `rm -i`, etc. Use
      --no-restore-processes to disable and only restore shells.

Usage:
    kitty_save_session.py                          # default path, capture procs
    kitty_save_session.py -o /tmp/session.conf     # custom path
    kitty_save_session.py --no-restore-processes   # shells + cwds only
    kitty_save_session.py --stdout                 # print, do not write
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

DEFAULT_OUT = Path.home() / ".config" / "kitty" / "sessions" / "restore.conf"

# Executables treated as "just a shell prompt" -- their argv is not re-launched
# because a bare `launch` already spawns the user's login shell.
SHELL_EXES = frozenset(
    {
        "bash",
        "csh",
        "dash",
        "fish",
        "ksh",
        "login",
        "sh",
        "tcsh",
        "zsh",
    }
)


def die(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def fetch_layout() -> list[dict]:
    proc = subprocess.run(["kitty", "@", "ls"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        die(
            "`kitty @ ls` failed -- is remote control enabled? "
            "Add `allow_remote_control yes` to kitty.conf.\n"
            f"stderr: {proc.stderr.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        die(f"could not parse `kitty @ ls` output as JSON: {e}")
        return []  # unreachable, keeps type-checkers happy


def _exe_basename(argv0: str) -> str:
    # Login shells appear as "-zsh" / "-bash" in argv[0]; strip the dash.
    name = Path(argv0).name
    if name.startswith("-"):
        name = name[1:]
    return name


def foreground_command(window: dict) -> list[str] | None:
    """Return argv of the topmost non-shell foreground process, or None.

    kitty reports `foreground_processes` per window (usually a single entry
    for the process attached to the pty; a pipeline like `a | b` shows both).
    We skip shell entries so idle windows return None -- their session line
    is a plain `launch`, which spawns the user's login shell.
    """
    for proc in window.get("foreground_processes", []) or []:
        cmdline = proc.get("cmdline") or []
        if not cmdline:
            continue
        if _exe_basename(cmdline[0]) in SHELL_EXES:
            continue
        return list(cmdline)
    return None


def render_session(data: list[dict], restore_processes: bool) -> str:
    lines: list[str] = []
    for os_idx, osw in enumerate(data):
        if os_idx > 0:
            lines.append("new_os_window")
            lines.append("")
        for tab in osw.get("tabs", []):
            title = (tab.get("title") or "").strip()
            lines.append(f"new_tab {title}".rstrip())
            layout = tab.get("layout") or ""
            if layout:
                lines.append(f"layout {layout}")

            windows = tab.get("windows", [])
            focused_window_id = None
            for w in windows:
                if w.get("is_focused"):
                    focused_window_id = w.get("id")
                    break

            for w in windows:
                cwd = w.get("cwd") or ""
                if cwd:
                    lines.append(f"cd {shlex.quote(cwd)}")
                w_title = (w.get("title") or "").strip()
                if w_title:
                    lines.append(f"title {w_title}")

                cmd = foreground_command(w) if restore_processes else None
                if cmd:
                    # `launch <argv...>` runs the program directly (no shell
                    # wrapping). shlex.join escapes each argument safely.
                    lines.append(f"launch {shlex.join(cmd)}")
                else:
                    lines.append("launch")

                if w.get("id") == focused_window_id:
                    lines.append("focus")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def summarize(data: list[dict], restore_processes: bool) -> str:
    os_count = len(data)
    tab_count = sum(len(osw.get("tabs", [])) for osw in data)
    windows = [w for osw in data for t in osw.get("tabs", []) for w in t.get("windows", [])]
    win_count = len(windows)
    proc_count = sum(1 for w in windows if foreground_command(w)) if restore_processes else 0
    base = f"{os_count} OS window(s), {tab_count} tab(s), {win_count} window(s)"
    if restore_processes:
        base += f", {proc_count} live process(es) captured"
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Session file path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print session file to stdout instead of writing to disk",
    )
    parser.add_argument(
        "--no-restore-processes",
        dest="restore_processes",
        action="store_false",
        help=(
            "Do not capture foreground commands; restore shell+cwd only. "
            "Use this if you have non-idempotent commands running "
            "(docker run, kubectl apply, ...) that must not re-run on restore."
        ),
    )
    parser.set_defaults(restore_processes=True)
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Do not print the summary after writing",
    )
    args = parser.parse_args()

    data = fetch_layout()
    content = render_session(data, restore_processes=args.restore_processes)

    if args.stdout:
        sys.stdout.write(content)
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content)

    if not args.quiet:
        print(f"OK: wrote {args.output} ({summarize(data, args.restore_processes)})")
        print(f"restore with: kitty --session {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
