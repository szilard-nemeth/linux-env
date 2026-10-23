#!/usr/bin/env python3
"""Keep the kitty restore session continuously fresh, via a launchd agent.

The problem this solves: kitty.conf sets `startup_session sessions/restore.conf`,
so every launch restores that one file -- but nothing wrote it unless you
remembered to run `kitty-save-session` by hand. Miss that, and a restart faithfully
restores a weeks-old layout.

Two save triggers, both served by this one long-lived process:

  * every --interval seconds (default 60), covering crashes and power loss;
  * once more on SIGTERM/SIGINT/SIGHUP, which is what launchd sends to user
    agents when the Mac logs out or restarts (see ExitTimeOut in
    `man launchd.plist`). That is the "saved right before reboot" case.

Every --snapshot-interval seconds (default 900) it also archives the on-screen
text of each window via kitty_snapshot_windows.py, pruned by age and by a total
size ceiling.

Write guards
------------
An autosave that fires every minute can silently destroy the only copy of a good
layout, so a save is skipped unless it is clearly an improvement:

  * kitty unreachable (not running, or `listen_on` not yet active) -> skip;
  * zero windows captured -> skip;
  * rendered layout identical to what is on disk -> skip (no churn, and no
    wasted backup slot);
  * window count collapsed to under half of what the file records -> skip for up
    to 3 consecutive ticks, then accept. This is the boot race: just after a
    restart kitty is still replaying the session, so a tick landing mid-restore
    would otherwise overwrite 13 windows with 3. The 3-tick cap means that
    deliberately closing most of your tabs still gets saved.

Writes are atomic (temp file + rename, fsync'd first) and the previous file is
copied into sessions/backups/ beforehand, keeping the newest 10.

Note on style: this uses argparse rather than click (which the repo's cursor rule
prefers for new code) because it must run under launchd on stdlib-only
/usr/bin/python3, with no access to the poetry venv. Its two sibling scripts in
this directory use argparse too.

Usage:
    kitty_session_autosave.py --install      # set up + start the launchd agent
    kitty_session_autosave.py --status       # is my session fresh? is it running?
    kitty_session_autosave.py --uninstall    # stop + remove the agent
    kitty_session_autosave.py --once         # one save cycle, then exit
    kitty_session_autosave.py                # run in the foreground (debugging)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import plistlib
import signal
import subprocess
import sys
import time
from pathlib import Path

# See the note in kitty_save_session.py: keeps __pycache__ out of
# ~/.linuxenv/scripts/kitty, which remove-stale-scripts would churn.
sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import kitty_session_lib as ksl  # noqa: E402

LABEL = "com.snemeth.kitty-session-autosave"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
SNAPSHOT_SCRIPT = SCRIPT_DIR / "kitty_snapshot_windows.py"

DEFAULT_LOG = ksl.SESSIONS_DIR / "autosave.log"
STATE_PATH = ksl.SESSIONS_DIR / ".autosave-state.json"

DEFAULT_INTERVAL = 60
DEFAULT_SNAPSHOT_INTERVAL = 900  # 15 minutes
DEFAULT_PRUNE_DAYS = 7
DEFAULT_MAX_BYTES = 2 * 1024**3  # 2 GiB

# A new capture with fewer than this fraction of the recorded window count is
# treated as suspect (see "Write guards" above).
SHRINK_RATIO = 0.5
SHRINK_GRACE = 3

# Statuses that mean "kitty told us nothing", so there is nothing to snapshot.
SKIP_NO_KITTY = "skip: kitty unreachable"
SKIP_NO_WINDOWS = "skip: no windows captured"

# launchd does not rotate its redirect files; trimmed once at startup.
LOG_MAX_BYTES = 2 * 1024 * 1024

# Absolute, always-present interpreter: launchd has no asdf/homebrew shims and
# no poetry venv.
SYSTEM_PYTHON = "/usr/bin/python3"

_stopping = False
_stop_signal = 0


def _request_stop(signum, _frame) -> None:
    """Signal handler: set flags only.

    Deliberately does no I/O. Python runs handlers in the main thread between
    bytecodes, so a print() here while the main thread is already inside
    print() would re-enter a non-reentrant buffer lock -- a deadlock on the
    one code path that must not hang. The message is logged by the main loop.
    """
    global _stopping, _stop_signal
    _stopping = True
    _stop_signal = signum


def log(msg: str) -> None:
    """Timestamped line to stdout (launchd redirects it to the log file)."""
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{stamp} {msg}", flush=True)


# --------------------------------------------------------------------------
# Persisted state
# --------------------------------------------------------------------------


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
    except OSError as e:
        log(f"warn: could not write state file {STATE_PATH}: {e}")


# --------------------------------------------------------------------------
# The save cycle
# --------------------------------------------------------------------------


def save_layout(
    session_path: Path,
    restore_processes: bool,
    state: dict,
    force: bool = False,
    denylist=None,
    to: str | None = None,
) -> str:
    """Capture and conditionally write the session file. Returns a status word."""
    data = ksl.collect_layout(to=to, log=log)
    if not data:
        return SKIP_NO_KITTY

    windows = ksl.count_windows(data)
    if windows == 0:
        return SKIP_NO_WINDOWS

    content = ksl.render_session(
        data,
        restore_processes=restore_processes,
        generator="kitty_session_autosave.py",
        denylist=denylist,
    )

    if not force and session_path.is_file():
        try:
            old = session_path.read_text()
        except OSError:
            old = ""
        if old:
            if ksl.strip_header(old) == ksl.strip_header(content):
                return "skip: unchanged"

            previous = ksl.header_int(ksl.parse_header(old), "windows")
            if previous and windows < previous * SHRINK_RATIO:
                skips = int(state.get("shrink_skips", 0))
                if skips < SHRINK_GRACE:
                    state["shrink_skips"] = skips + 1
                    return (
                        f"skip: window count collapsed {previous} -> {windows} " f"(guard {skips + 1}/{SHRINK_GRACE})"
                    )
                log(f"shrink guard exhausted after {skips} skip(s); accepting {windows} window(s)")

    ksl.rotate_backup(session_path)
    ksl.atomic_write(session_path, content)
    state["shrink_skips"] = 0
    return f"wrote: {ksl.summarize(data, restore_processes, denylist)}"


def run_snapshot(extent: str, prune_days: int, max_bytes: int) -> str:
    """Archive per-window text by delegating to the snapshot script."""
    cmd = [
        sys.executable,
        str(SNAPSHOT_SCRIPT),
        "--quiet",
        "--prune-days",
        str(prune_days),
        "--max-bytes",
        str(max_bytes),
    ]
    if extent == "all":
        cmd.append("--scrollback")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
    except subprocess.TimeoutExpired:
        return "snapshot failed: timed out after 300s"
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        return f"snapshot failed: {detail[-1] if detail else f'exit {proc.returncode}'}"
    return f"snapshot ok (total {ksl.human_bytes(ksl.dir_size(ksl.SNAPSHOT_ROOT))})"


def tick(args, state: dict, force: bool = False, final: bool = False, verbose: bool = False) -> None:
    session_path = Path(args.output)

    try:
        status = save_layout(
            session_path,
            args.restore_processes,
            state,
            force=force,
            denylist=ksl.compile_denylist(args.process_denylist or None),
            to=args.to,
        )
    except Exception as e:  # never let one bad cycle kill the daemon
        status = f"error: {e}"
    # In the daemon, skips are the common case and logging them every minute
    # would bury the real events; an interactive --once always reports, because
    # silence there looks like a hang.
    if verbose or not status.startswith("skip:"):
        log(status)

    # Never snapshot on the way out. `get-text --extent all` over a 200k-line
    # scrollback can take far longer than launchd's ExitTimeOut, and being
    # SIGKILLed mid-snapshot would risk the layout save we actually came for.
    # (The layout save above has already completed by this point.)
    if final:
        save_state(state)
        return

    # If kitty could not be reached there is nothing to snapshot either, so
    # don't spawn a subprocess that is guaranteed to fail.
    if status in (SKIP_NO_KITTY, SKIP_NO_WINDOWS):
        save_state(state)
        return

    if args.snapshot_interval <= 0:
        save_state(state)
        return

    now = time.time()
    last = float(state.get("last_snapshot", 0) or 0)
    due = args.snapshot_now or (now - last) >= args.snapshot_interval
    if due:
        try:
            result = run_snapshot(args.snapshot_extent, args.prune_days, args.max_bytes)
            log(result)
            # Only mark it done on success, so a transient failure is retried
            # on the next tick instead of waiting out the whole interval.
            if not result.startswith("snapshot failed"):
                state["last_snapshot"] = now
        except Exception as e:
            log(f"error: snapshot cycle failed: {e}")

    save_state(state)


def run_forever(args, state: dict) -> int:
    log(
        f"autosave started (pid {os.getpid()}): layout every {args.interval}s, "
        f"text snapshot every {args.snapshot_interval}s (extent={args.snapshot_extent}), "
        f"session={args.output}"
    )
    if not ksl.discover_sockets():
        log(f"warn: {ksl.unreachable_hint()}")

    while not _stopping:
        tick(args, state)
        # Interruptible sleep in 1s steps. PEP 475 makes time.sleep() resume
        # for its remaining duration after a handler returns, so a single
        # sleep(interval) would swallow SIGTERM for up to a full interval and
        # miss launchd's ExitTimeOut window. Stepping bounds that to ~1s.
        for _ in range(args.interval):
            if _stopping:
                break
            time.sleep(1)

    name = signal.Signals(_stop_signal).name if _stop_signal else "stop request"
    log(f"received {name}; final save before exit")
    tick(args, state, final=True)
    log("autosave stopped")
    return 0


# --------------------------------------------------------------------------
# launchd agent management
# --------------------------------------------------------------------------


def domain() -> str:
    return f"gui/{os.getuid()}"


def launchctl(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *cmd], capture_output=True, text=True, check=False)


def python_for_agent() -> str:
    return SYSTEM_PYTHON if Path(SYSTEM_PYTHON).exists() else sys.executable


def build_plist(args, script_path: Path, log_path: Path) -> dict:
    program = [
        python_for_agent(),
        str(script_path),
        "--interval",
        str(args.interval),
        "--snapshot-interval",
        str(args.snapshot_interval),
        "--snapshot-extent",
        args.snapshot_extent,
        "--prune-days",
        str(args.prune_days),
        "--max-bytes",
        str(args.max_bytes),
        "--output",
        str(args.output),
    ]
    if not args.restore_processes:
        program.append("--no-restore-processes")
    for pattern in args.process_denylist or []:
        program += ["--process-denylist", pattern]

    kitty_dir = str(Path(ksl.MACOS_KITTY_BIN).parent)
    return {
        "Label": LABEL,
        "ProgramArguments": program,
        "RunAtLoad": True,
        # Always-on housekeeping: respawn if it ever crashes.
        "KeepAlive": True,
        # Room for the final save on the way down. `man launchd.plist` warns a
        # value of 0 means infinity and can stall shutdown forever.
        "ExitTimeOut": 20,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "Nice": 5,
        "StandardOutPath": str(log_path),
        "StandardErrorPath": str(log_path),
        "EnvironmentVariables": {
            # launchd starts agents with a minimal PATH that lacks kitty.
            "PATH": f"{kitty_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
            # Keeps __pycache__ out of ~/.linuxenv/scripts/kitty (see the note
            # at the top of this file).
            "PYTHONDONTWRITEBYTECODE": "1",
            # Otherwise tracebacks sit in a buffer and the log looks dead.
            "PYTHONUNBUFFERED": "1",
        },
        "WorkingDirectory": str(Path.home()),
    }


def install(args) -> int:
    script_path = Path(args.script_path).expanduser().resolve() if args.script_path else Path(__file__).resolve()
    if not script_path.is_file():
        ksl.die(f"script path does not exist: {script_path}")

    log_path = Path(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = build_plist(args, script_path, log_path)
    with open(PLIST_PATH, "wb") as fh:
        plistlib.dump(data, fh)
    print(f"OK: wrote {PLIST_PATH}")

    # Replace any previous incarnation. bootout fails when not loaded; ignore.
    launchctl("bootout", f"{domain()}/{LABEL}")
    proc = launchctl("bootstrap", domain(), str(PLIST_PATH))
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        ksl.die(f"launchctl bootstrap failed: {detail}")

    print(f"OK: loaded agent {LABEL}")
    print(f"     runs: {' '.join(data['ProgramArguments'][:2])} ...")
    print(f"     log:  {log_path}")
    if not ksl.discover_sockets():
        print(f"\nWARN: {ksl.unreachable_hint()}")
        print("      Until then the agent runs but every save is skipped.")
    print("\ncheck with: kitty-autosave-status")
    return 0


def uninstall(_args) -> int:
    proc = launchctl("bootout", f"{domain()}/{LABEL}")
    if proc.returncode == 0:
        print(f"OK: unloaded agent {LABEL}")
    else:
        print(f"note: agent was not loaded ({(proc.stderr or proc.stdout).strip()})")

    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
        print(f"OK: removed {PLIST_PATH}")
    else:
        print(f"note: no plist at {PLIST_PATH}")
    print("note: session file, backups and snapshots were left untouched")
    return 0


def agent_state() -> str:
    proc = launchctl("print", f"{domain()}/{LABEL}")
    if proc.returncode != 0:
        return "not loaded"
    pid = last_exit = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("pid = "):
            pid = line.split("=", 1)[1].strip()
        elif line.startswith("last exit code = "):
            last_exit = line.split("=", 1)[1].strip()
    if pid:
        return f"running (pid {pid})"
    return f"loaded but not running (last exit code {last_exit or 'unknown'})"


def status(args) -> int:
    session_path = Path(args.output)
    print("kitty session autosave status")
    print("-" * 60)

    print(f"agent:    {agent_state()}")
    print(f"plist:    {PLIST_PATH if PLIST_PATH.exists() else '(none) -- run kitty-autosave-install'}")

    sockets = ksl.discover_sockets()
    if sockets:
        print(f"kitty:    reachable ({len(sockets)} live socket(s))")
    else:
        print("kitty:    NOT reachable")
        print(f"          {ksl.unreachable_hint()}")

    print()
    if session_path.is_file():
        age = time.time() - session_path.stat().st_mtime
        header = ksl.parse_header(session_path.read_text())
        counts = ", ".join(f"{k}={header[k]}" for k in ("os_windows", "tabs", "windows") if k in header)
        print(f"session:  {session_path}")
        print(f"          saved {ksl.human_age(age)} ago" + (f" ({counts})" if counts else ""))
        if age > 3600:
            print("          WARN: over an hour old -- autosave may not be running")
    else:
        print(f"session:  {session_path} does not exist yet")

    backups = ksl.backup_dir_for(session_path)
    if backups.is_dir():
        files = sorted(backups.glob(f"{session_path.stem}.*{session_path.suffix}"))
        print(f"backups:  {len(files)} in {backups}")

    snaps = (
        [p for p in ksl.SNAPSHOT_ROOT.iterdir() if p.is_dir() and not p.is_symlink()]
        if (ksl.SNAPSHOT_ROOT.is_dir())
        else []
    )
    if snaps:
        newest = max(snaps, key=lambda p: p.name)
        newest_age = time.time() - newest.stat().st_mtime
        print(
            f"snapshots: {len(snaps)} dirs, {ksl.human_bytes(ksl.dir_size(ksl.SNAPSHOT_ROOT))}, "
            f"newest {ksl.human_age(newest_age)} ago"
        )
    else:
        print("snapshots: none yet")

    log_path = Path(args.log_file)
    if log_path.is_file():
        lines = log_path.read_text(errors="replace").splitlines()
        print(f"\nlog tail ({log_path}):")
        for line in lines[-8:]:
            print(f"  {line}")
    return 0


def trim_log(path: Path) -> None:
    """Keep the log bounded; launchd itself never rotates its redirect files."""
    try:
        if not path.is_file() or path.stat().st_size <= LOG_MAX_BYTES:
            return
        lines = path.read_text(errors="replace").splitlines()[-500:]
        path.write_text("\n".join(lines) + "\n")
    except OSError:
        pass


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--install", action="store_true", help="Write and load the launchd agent, then exit")
    mode.add_argument("--uninstall", action="store_true", help="Unload and remove the launchd agent, then exit")
    mode.add_argument("--status", action="store_true", help="Report freshness, agent state and reachability")
    mode.add_argument("--once", action="store_true", help="Run a single save cycle and exit")

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ksl.DEFAULT_SESSION,
        help=f"Session file to keep fresh (default: {ksl.DEFAULT_SESSION})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Seconds between layout saves (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--snapshot-interval",
        type=int,
        default=DEFAULT_SNAPSHOT_INTERVAL,
        help=f"Seconds between window-text snapshots; 0 disables (default: {DEFAULT_SNAPSHOT_INTERVAL})",
    )
    parser.add_argument(
        "--snapshot-extent",
        choices=("screen", "all"),
        default="all",
        help="How much window text to archive: visible screen, or screen + full scrollback (default: all)",
    )
    parser.add_argument(
        "--snapshot-now",
        action="store_true",
        help="Force a text snapshot on the next cycle regardless of schedule",
    )
    parser.add_argument(
        "--prune-days",
        type=int,
        default=DEFAULT_PRUNE_DAYS,
        help=f"Delete snapshots older than N days (default: {DEFAULT_PRUNE_DAYS})",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"Total size ceiling for snapshots (default: {DEFAULT_MAX_BYTES})",
    )
    parser.add_argument(
        "--no-restore-processes",
        dest="restore_processes",
        action="store_false",
        help="Capture shell+cwd only; do not re-launch foreground commands on restore",
    )
    parser.set_defaults(restore_processes=True)
    parser.add_argument(
        "--to",
        metavar="ADDRESS",
        help=(
            "Pin a kitty remote-control address, e.g. unix:/path/to/kitty.sock-123. "
            "Default: the ambient instance, falling back to every live socket."
        ),
    )
    parser.add_argument(
        "--process-denylist",
        action="append",
        metavar="REGEX",
        help=(
            "Regex for commands that must never be re-launched on restore. "
            "Repeatable. Replaces the default list "
            f"({', '.join(ksl.DEFAULT_PROCESS_DENYLIST)}). "
            "Example: --process-denylist '^claude\\b' to stop agent sessions "
            "being respawned in every window at launch."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --once, bypass the unchanged/shrink write guards",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG,
        help=f"Where the agent's output is written (default: {DEFAULT_LOG})",
    )
    parser.add_argument(
        "--script-path",
        help="With --install, the script path to record in the plist (default: this file)",
    )
    args = parser.parse_args()

    if args.install:
        return install(args)
    if args.uninstall:
        return uninstall(args)
    if args.status:
        return status(args)

    state = load_state()

    if args.once:
        tick(args, state, force=args.force, verbose=True)
        return 0

    trim_log(Path(args.log_file))
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, _request_stop)
    return run_forever(args, state)


if __name__ == "__main__":
    sys.exit(main())
