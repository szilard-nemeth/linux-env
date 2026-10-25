#!/usr/bin/env python3
"""Snapshot the current kitty layout to a session file for later restore.

Queries the running kitty via `kitty @ ls`, then writes a session file with
one entry per OS window / tab / window (all tabs, their titles, layouts,
working directories, and -- by default -- the currently-running foreground
command in each window). Restore with:

    kitty --session <file>

or set `startup_session <file>` in kitty.conf so it happens on launch.

Requires `allow_remote_control yes` in kitty.conf. To be reachable from a
process without a controlling terminal, kitty.conf also needs
`listen_on unix:${HOME}/.config/kitty/kitty.sock` -- see kitty_session_lib.py.

For this to stay fresh without you thinking about it, see
kitty_session_autosave.py, which runs this capture every minute and once more
when the Mac logs out or restarts.

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
import sys
from pathlib import Path

# Importing a sibling module would create scripts/kitty/__pycache__ in the copy
# under ~/.linuxenv, which setup-env.sh's remove-stale-scripts would then move
# aside on every shell load (the repo has no such dir to diff against).
sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import kitty_session_lib as ksl  # noqa: E402

DEFAULT_OUT = ksl.DEFAULT_SESSION


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
        "--to",
        metavar="ADDRESS",
        help=(
            "kitty remote-control address, e.g. unix:/path/to/kitty.sock-123. "
            "Default: the ambient instance ($KITTY_LISTEN_ON or controlling "
            "terminal), falling back to every live socket found."
        ),
    )
    parser.add_argument(
        "--no-backup",
        dest="backup",
        action="store_false",
        help="Do not copy the previous session file into the backups/ dir first",
    )
    parser.set_defaults(backup=True)
    parser.add_argument(
        "--process-denylist",
        action="append",
        metavar="REGEX",
        help=(
            "Regex for commands that must never be re-launched on restore. "
            "Repeatable. Replaces the default list "
            f"({', '.join(ksl.DEFAULT_PROCESS_DENYLIST)})."
        ),
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="List discovered kitty control sockets and exit (debugging aid)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Do not print the summary after writing",
    )
    args = parser.parse_args()

    if args.list_targets:
        sockets = ksl.discover_sockets()
        if not sockets:
            print(f"no live kitty sockets. {ksl.unreachable_hint()}")
            return 1
        for sock in sockets:
            print(f"{ksl.socket_address(sock)}")
        return 0

    denylist = ksl.compile_denylist(args.process_denylist or None)
    data = ksl.collect_layout(to=args.to, log=lambda m: print(m, file=sys.stderr))
    if not data:
        ksl.die(f"`kitty @ ls` returned no windows -- {ksl.unreachable_hint()}")

    content = ksl.render_session(
        data,
        restore_processes=args.restore_processes,
        generator="kitty_save_session.py",
        denylist=denylist,
    )

    if args.stdout:
        sys.stdout.write(content)
        return 0

    if args.backup:
        ksl.rotate_backup(args.output)
    ksl.atomic_write(args.output, content)

    if not args.quiet:
        print(f"OK: wrote {args.output} ({ksl.summarize(data, args.restore_processes, denylist)})")
        print(f"restore with: kitty --session {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
