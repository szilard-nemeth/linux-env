#!/usr/bin/env python3
"""Shared helpers for the kitty session save / snapshot / autosave scripts.

Imported as a sibling module by kitty_save_session.py, kitty_snapshot_windows.py
and kitty_session_autosave.py (all three live in this directory, which is on PATH
via setup-env.sh). Stdlib only -- no third-party imports -- because
kitty_session_autosave.py runs under launchd with /usr/bin/python3 and has no
access to the poetry venv.

Reaching kitty from a background process
----------------------------------------
`kitty @ <cmd>` resolves its target in this order:

    --to <address>  ->  $KITTY_LISTEN_ON  ->  the controlling terminal

A launchd job has no controlling terminal and no KITTY_LISTEN_ON, so it can only
reach kitty over a socket. That requires this in kitty.conf::

    listen_on unix:${HOME}/.config/kitty/kitty.sock

kitty appends "-<pid>" to that value (it only substitutes in place when the
value contains {kitty_pid}), so the real socket is e.g. kitty.sock-752 and
callers must glob. Each running kitty instance gets its own socket, and sockets
belonging to dead instances can linger, hence discover_sockets() filters on
both "is a socket" and "pid is alive".
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

KITTY_CONFIG_DIR = Path.home() / ".config" / "kitty"
SESSIONS_DIR = KITTY_CONFIG_DIR / "sessions"
DEFAULT_SESSION = SESSIONS_DIR / "restore.conf"
SNAPSHOT_ROOT = KITTY_CONFIG_DIR / "snapshots"

# Must match the `listen_on` value in config/kitty.conf. The real sockets are
# this path with "-<pid>" appended.
SOCKET_BASE = KITTY_CONFIG_DIR / "kitty.sock"

# Fallback when `kitty` is not on PATH, which is the normal case under launchd.
MACOS_KITTY_BIN = "/Applications/kitty.app/Contents/MacOS/kitty"

# How long to wait on a single `kitty @` call before giving up. get-text on a
# huge scrollback is the slow case; a hung call must never wedge the daemon.
REMOTE_TIMEOUT = 30

# Deep enough to be useful: a bad capture is usually noticed hours later, after
# a reboot, and these files are ~3 KB each.
DEFAULT_BACKUP_KEEP = 50

# Session files and their backups record full command lines, which can contain
# tokens and other secrets, so they are not world-readable.
FILE_MODE = 0o600

# Transient commands that must not be re-launched on restore: remote-control
# one-shots that have already finished, and short-lived utilities. Extend with
# --process-denylist (e.g. to stop long-running agents being respawned).
DEFAULT_PROCESS_DENYLIST = (
    # `kitty @ ...` / `kitten @ ...`: a remote-control one-shot that has already
    # run. Note "@" is not a word character, so no \b after it.
    r"^(kitty|kitten)\b.*\s@(\s|$)",
    r"^caffeinate\b",
)

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

HEADER_PREFIX = "#:: "


def die(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def kitty_bin() -> str:
    """Absolute path to the kitty executable."""
    found = shutil.which("kitty")
    if found:
        return found
    return MACOS_KITTY_BIN


# --------------------------------------------------------------------------
# Remote control
# --------------------------------------------------------------------------


def discover_sockets() -> list[Path]:
    """Return kitty control sockets of *live* kitty instances, newest first.

    Skips leftover socket files whose kitty process is gone, so a crashed
    instance cannot make callers think kitty is still reachable.
    """
    candidates = sorted(
        SOCKET_BASE.parent.glob(f"{SOCKET_BASE.name}-*"),
        key=lambda p: _mtime(p),
        reverse=True,
    )
    live: list[Path] = []
    for path in candidates:
        try:
            if not stat.S_ISSOCK(path.stat().st_mode):
                continue
        except OSError:
            continue
        pid_part = path.name.rsplit("-", 1)[-1]
        if not pid_part.isdigit():
            continue
        if not _pid_alive(int(pid_part)):
            continue
        live.append(path)
    return live


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Exists but owned by someone else; not ours to talk to.
        return False
    except OSError:
        return False
    return True


def kitty_remote(args: list[str], to: str | None = None) -> subprocess.CompletedProcess:
    """Run `kitty @ [--to <to>] <args...>` and return the completed process."""
    cmd = [kitty_bin(), "@"]
    if to:
        cmd += ["--to", to]
    cmd += args
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=REMOTE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 1, "", f"timed out after {REMOTE_TIMEOUT}s")
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 1, "", f"kitty executable not found at {kitty_bin()}")


def socket_address(path: Path) -> str:
    return f"unix:{path}"


def kitty_ls(to: str | None = None) -> list[dict] | None:
    """Return parsed `kitty @ ls` output, or None if unreachable/unparseable."""
    proc = kitty_remote(["ls"], to=to)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def collect_layout(to: str | None = None, ambient_first: bool = True, log=None) -> list[dict]:
    """Return the OS-window list of the richest reachable kitty instance.

    `to` pins a single address. Otherwise, when `ambient_first` is set, the
    ambient channel ($KITTY_LISTEN_ON or the controlling terminal) is tried
    first -- that is what manual in-kitty invocations have always used, so their
    behaviour is unchanged. Failing that, every live socket is queried.

    With more than one live instance the one with the most windows wins rather
    than merging them: merging would collapse two instances into one instance
    with several OS windows, so whichever instance launched next would restore
    *both* sets of windows.
    """
    if to:
        return kitty_ls(to) or []

    if ambient_first:
        data = kitty_ls(None)
        if data:
            return data

    best: list[dict] = []
    reachable = 0
    for sock in discover_sockets():
        data = kitty_ls(socket_address(sock))
        if not data:
            continue
        reachable += 1
        if count_windows(data) > count_windows(best):
            best = data
    if reachable > 1 and log:
        log(f"warn: {reachable} live kitty instances; kept the richest ({count_windows(best)} window(s))")
    return best


def unreachable_hint() -> str:
    """Explain why kitty could not be reached, with the fix."""
    if not discover_sockets():
        return (
            "no live kitty control socket found. Add "
            "`listen_on unix:${HOME}/.config/kitty/kitty.sock` to kitty.conf "
            "(config/kitty.conf in the linux-env repo), then fully quit and "
            "relaunch kitty -- a config reload is not enough. Also ensure "
            "`allow_remote_control yes` is set."
        )
    return "a kitty socket exists but `kitty @ ls` failed; check `allow_remote_control` in kitty.conf."


# --------------------------------------------------------------------------
# Layout inspection
# --------------------------------------------------------------------------


def _exe_basename(argv0: str) -> str:
    # Login shells appear as "-zsh" / "-bash" in argv[0]; strip the dash.
    name = Path(argv0).name
    if name.startswith("-"):
        name = name[1:]
    return name


def compile_denylist(patterns=None) -> list:
    """Compile process-denylist regexes (defaults applied when None)."""
    if patterns is None:
        patterns = DEFAULT_PROCESS_DENYLIST
    return [re.compile(p) for p in patterns]


def foreground_command(window: dict, denylist=None) -> list[str] | None:
    """Return argv of the topmost non-shell foreground process, or None.

    kitty reports `foreground_processes` per window (usually a single entry
    for the process attached to the pty; a pipeline like `a | b` shows both).
    We skip shell entries so idle windows return None -- their session line
    is a plain `launch`, which spawns the user's login shell.

    Commands matching `denylist` are also skipped, so transient or expensive
    processes are not silently re-run on every restore.
    """
    if denylist is None:
        denylist = compile_denylist()
    for proc in window.get("foreground_processes", []) or []:
        cmdline = proc.get("cmdline") or []
        if not cmdline:
            continue
        if _exe_basename(cmdline[0]) in SHELL_EXES:
            continue
        # Match patterns against both the raw command line and a form with
        # argv[0] reduced to its basename: kitty reports absolute paths, so an
        # intuitive pattern like `^claude\b` would otherwise never anchor.
        probes = (
            " ".join(cmdline),
            " ".join([_exe_basename(cmdline[0])] + list(cmdline[1:])),
        )
        if any(rx.search(p) for rx in denylist for p in probes):
            continue
        return list(cmdline)
    return None


def _focus_target(data: list[dict]) -> tuple[int, int, object] | None:
    """Locate the single window that should be focused on restore.

    Needed because kitty reports `is_focused` for the active window of *every*
    tab in the focused OS window (tabs.py: `w.os_window_id ==
    current_focused_os_window_id() and w is active_window`), so it cannot be
    used per-tab. Meanwhile session.py's `focus` applies to the tab being built
    at that point and overwrites any earlier one, so emitting it per tab means
    the last tab always wins. Exactly one `focus` must therefore be emitted.

    Returns (os_window_index, tab_index, window_id), or None.
    """
    fallback = None
    for os_idx, osw in enumerate(data):
        for tab_idx, tab in enumerate(osw.get("tabs", []) or []):
            windows = tab.get("windows", []) or []
            wid = None
            for key in ("is_active", "is_focused"):
                for w in windows:
                    if w.get(key):
                        wid = w.get("id")
                        break
                if wid is not None:
                    break
            if wid is None:
                continue
            if tab.get("is_focused"):
                return (os_idx, tab_idx, wid)
            if fallback is None and tab.get("is_active"):
                fallback = (os_idx, tab_idx, wid)
    return fallback


def iter_windows(data: list[dict]):
    for osw in data:
        for tab in osw.get("tabs", []) or []:
            for window in tab.get("windows", []) or []:
                yield window


def count_windows(data: list[dict]) -> int:
    return sum(1 for _ in iter_windows(data))


def counts(data: list[dict]) -> dict:
    return {
        "os_windows": len(data),
        "tabs": sum(len(osw.get("tabs", []) or []) for osw in data),
        "windows": count_windows(data),
    }


def summarize(data: list[dict], restore_processes: bool, denylist=None) -> str:
    c = counts(data)
    base = f"{c['os_windows']} OS window(s), {c['tabs']} tab(s), {c['windows']} window(s)"
    if restore_processes:
        if denylist is None:
            denylist = compile_denylist()
        proc_count = sum(1 for w in iter_windows(data) if foreground_command(w, denylist))
        base += f", {proc_count} live process(es) captured"
    return base


# --------------------------------------------------------------------------
# Session file rendering
# --------------------------------------------------------------------------


def render_session(
    data: list[dict],
    restore_processes: bool,
    header: bool = True,
    generator: str | None = None,
    denylist=None,
) -> str:
    """Render `kitty @ ls` output as a kitty session file.

    The optional header is a block of `#::`-prefixed comments recording when the
    file was written and how much it contained. kitty's session parser skips any
    line starting with "#", so this is inert at restore time; it exists so
    staleness and a sudden collapse in window count are both detectable later
    without a separate state file.
    """
    lines: list[str] = []

    if header:
        c = counts(data)
        lines.append(f"{HEADER_PREFIX}kitty session file -- generated, do not edit by hand")
        lines.append(f"{HEADER_PREFIX}saved_at: {datetime.datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"{HEADER_PREFIX}os_windows: {c['os_windows']}")
        lines.append(f"{HEADER_PREFIX}tabs: {c['tabs']}")
        lines.append(f"{HEADER_PREFIX}windows: {c['windows']}")
        lines.append(f"{HEADER_PREFIX}restore_processes: {'yes' if restore_processes else 'no'}")
        if generator:
            lines.append(f"{HEADER_PREFIX}generator: {generator}")
        lines.append("")

    if denylist is None:
        denylist = compile_denylist()
    target = _focus_target(data)

    for os_idx, osw in enumerate(data):
        if os_idx > 0:
            lines.append("new_os_window")
            lines.append("")
        # Marks which OS window gets focus; only meaningful with several.
        if target and len(data) > 1 and target[0] == os_idx:
            lines.append("focus_os_window")
            lines.append("")

        for tab_idx, tab in enumerate(osw.get("tabs", []) or []):
            title = (tab.get("title") or "").strip()
            lines.append(f"new_tab {title}".rstrip())
            layout = tab.get("layout") or ""
            if layout:
                lines.append(f"layout {layout}")

            windows = tab.get("windows", []) or []
            for w in windows:
                cwd = w.get("cwd") or ""
                if cwd:
                    lines.append(f"cd {shlex.quote(cwd)}")
                w_title = (w.get("title") or "").strip()
                if w_title:
                    lines.append(f"title {w_title}")

                cmd = foreground_command(w, denylist) if restore_processes else None
                if cmd:
                    # `launch <argv...>` runs the program directly (no shell
                    # wrapping). shlex.join escapes each argument safely.
                    lines.append(f"launch {shlex.join(cmd)}")
                else:
                    lines.append("launch")

                # Exactly one focus for the whole file -- see _focus_target.
                if target and (os_idx, tab_idx, w.get("id")) == target:
                    lines.append("focus")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_header(text: str) -> dict:
    """Parse the `#::` header block of a rendered session file.

    Returns {} when the text has no such header (e.g. a file written before
    headers existed, or one produced with header=False).
    """
    out: dict = {}
    for line in text.splitlines():
        if not line.startswith(HEADER_PREFIX):
            if line.strip() and not line.startswith("#"):
                break  # past the header block
            continue
        body = line[len(HEADER_PREFIX) :].strip()
        if ": " not in body:
            continue
        key, _, value = body.partition(": ")
        out[key.strip()] = value.strip()
    return out


def header_int(header: dict, key: str) -> int | None:
    raw = header.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def strip_header(text: str) -> str:
    """Drop the leading comment/blank block so two renders can be compared.

    Without this, the embedded timestamp would make every render differ and
    defeat change detection.
    """
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and (not lines[idx].strip() or lines[idx].startswith("#")):
        idx += 1
    return "\n".join(lines[idx:]).strip()


# --------------------------------------------------------------------------
# Durable writes
# --------------------------------------------------------------------------


def atomic_write(path: Path, content: str, mode: int = FILE_MODE) -> None:
    """Write `content` to `path` atomically.

    The temp file is created in the target's own directory so os.replace() is a
    same-filesystem rename, and is fsync'd first. A crash or a shutdown kill
    mid-write therefore leaves the previous file intact rather than a truncated
    session file that would restore nothing.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def backup_dir_for(path: Path) -> Path:
    return path.parent / "backups"


def rotate_backup(path: Path, keep: int = DEFAULT_BACKUP_KEEP) -> Path | None:
    """Copy the current file aside before it is replaced; prune to `keep`.

    Backups are the recovery path if an autosave ever captures a layout you did
    not want (mid-restore, or right after you closed most of your tabs).
    """
    if not path.is_file():
        return None
    bdir = backup_dir_for(path)
    bdir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = bdir / f"{path.stem}.{stamp}{path.suffix}"
    counter = 1
    while dest.exists():
        dest = bdir / f"{path.stem}.{stamp}-{counter}{path.suffix}"
        counter += 1

    shutil.copy2(path, dest)
    prune_backups(path, keep)
    return dest


def prune_backups(path: Path, keep: int = DEFAULT_BACKUP_KEEP) -> int:
    """Keep only the newest `keep` backups of `path`. Returns how many went."""
    bdir = backup_dir_for(path)
    if not bdir.is_dir():
        return 0
    existing = sorted(bdir.glob(f"{path.stem}.*{path.suffix}"), key=_mtime, reverse=True)
    removed = 0
    for old in existing[keep:]:
        try:
            old.unlink()
            removed += 1
        except OSError:
            pass
    return removed


# --------------------------------------------------------------------------
# Misc
# --------------------------------------------------------------------------


def human_age(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def human_bytes(num: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(num) < 1024 or unit == "TiB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024
    return f"{num:.1f} TiB"


def dir_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total
