#!/usr/bin/env python3
"""Install recurring jobs declared in config/scheduled-jobs.json as launchd agents.

Why launchd and not Claude Code's /loop: /loop jobs live inside one Claude
session, die with it, and expire after 7 days. A job that must fire every day at
17:00 whether or not a terminal is open belongs to launchd. The descriptor keeps
the schedule in the repo; this script turns each entry into
~/Library/LaunchAgents/com.snemeth.job.<name>.plist and (re)loads it.

Each job runs `/bin/zsh -lc <command>`: a login shell, so .zprofile puts brew
and the asdf python3 on PATH, but no interactive aliases.

Like kitty_session_autosave.py this is stdlib-only argparse, so it works before
the poetry venv exists.

Usage:
    scheduled_jobs.py --list                 # what the descriptor declares
    scheduled_jobs.py --install [NAME ...]   # write + load agents (default: all enabled)
    scheduled_jobs.py --uninstall [NAME ...] # unload + remove agents (default: all ours)
    scheduled_jobs.py --status               # loaded? last exit code? log path
    scheduled_jobs.py --run NAME             # kick a loaded job now via launchctl
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

LABEL_PREFIX = "com.snemeth.job."
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LOG_DIR = Path.home() / "Library" / "Logs" / "linuxenv-jobs"
CALENDAR_KEYS = {"Minute", "Hour", "Day", "Weekday", "Month"}


def default_descriptor() -> Path:
    repo = os.environ.get("LINUXENV_DIR") or str(Path.home() / "development" / "my-repos" / "linux-env")
    return Path(repo).expanduser() / "config" / "scheduled-jobs.json"


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def label_for(name: str) -> str:
    return f"{LABEL_PREFIX}{name}"


def plist_path_for(name: str) -> Path:
    return LAUNCH_AGENTS_DIR / f"{label_for(name)}.plist"


def log_path_for(name: str) -> Path:
    return LOG_DIR / f"{name}.log"


def domain() -> str:
    return f"gui/{os.getuid()}"


def launchctl(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *cmd], capture_output=True, text=True, check=False)


# --------------------------------------------------------------------------
# Descriptor
# --------------------------------------------------------------------------


def validate_schedule(name: str, schedule) -> None:
    entries = schedule if isinstance(schedule, list) else [schedule]
    if not entries:
        die(f"job {name!r}: empty schedule")
    for entry in entries:
        if not isinstance(entry, dict) or not entry:
            die(f"job {name!r}: each schedule entry must be a non-empty object")
        unknown = set(entry) - CALENDAR_KEYS
        if unknown:
            die(f"job {name!r}: unknown schedule keys {sorted(unknown)} (allowed: {sorted(CALENDAR_KEYS)})")
        for key, value in entry.items():
            if not isinstance(value, int):
                die(f"job {name!r}: schedule {key} must be an integer, got {value!r}")


def load_jobs(path: Path) -> list[dict]:
    if not path.is_file():
        die(f"descriptor not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        die(f"{path}: invalid JSON: {e}")

    jobs = data.get("jobs", [])
    seen = set()
    for job in jobs:
        name = job.get("name")
        if not name or not all(c.isalnum() or c in "-_" for c in name):
            die(f"job name must be non-empty [A-Za-z0-9_-]: {name!r}")
        if name in seen:
            die(f"duplicate job name: {name!r}")
        seen.add(name)
        if not job.get("command"):
            die(f"job {name!r}: missing command")
        validate_schedule(name, job.get("schedule"))
        job.setdefault("enabled", True)
    return jobs


def select(jobs: list[dict], names: list[str]) -> list[dict]:
    if not names:
        return jobs
    by_name = {j["name"]: j for j in jobs}
    missing = [n for n in names if n not in by_name]
    if missing:
        die(f"not in descriptor: {', '.join(missing)}")
    return [by_name[n] for n in names]


def describe_schedule(schedule) -> str:
    entries = schedule if isinstance(schedule, list) else [schedule]
    parts = []
    for e in entries:
        hour = f"{e['Hour']:02d}" if "Hour" in e else "**"
        minute = f"{e['Minute']:02d}" if "Minute" in e else "**"
        extra = " ".join(f"{k}={e[k]}" for k in ("Weekday", "Day", "Month") if k in e)
        parts.append(f"{hour}:{minute}" + (f" {extra}" if extra else ""))
    return ", ".join(parts)


# --------------------------------------------------------------------------
# launchd agent management
# --------------------------------------------------------------------------


def build_plist(job: dict) -> dict:
    log_path = str(log_path_for(job["name"]))
    return {
        "Label": label_for(job["name"]),
        "ProgramArguments": ["/bin/zsh", "-lc", job["command"]],
        "StartCalendarInterval": job["schedule"],
        "RunAtLoad": False,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": log_path,
        "StandardErrorPath": log_path,
        "EnvironmentVariables": {"PYTHONUNBUFFERED": "1"},
        "WorkingDirectory": str(Path.home()),
    }


def install_job(job: dict) -> bool:
    name = job["name"]
    plist_path = plist_path_for(name)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(plist_path, "wb") as fh:
        plistlib.dump(build_plist(job), fh)

    # Replace any previous incarnation. bootout fails when not loaded; ignore.
    launchctl("bootout", f"{domain()}/{label_for(name)}")
    proc = launchctl("bootstrap", domain(), str(plist_path))
    if proc.returncode != 0:
        print(f"ERROR: {name}: launchctl bootstrap failed: {(proc.stderr or proc.stdout).strip()}")
        return False
    print(f"OK: {name} loaded, runs at {describe_schedule(job['schedule'])} (log: {log_path_for(name)})")
    return True


def uninstall_job(name: str) -> None:
    proc = launchctl("bootout", f"{domain()}/{label_for(name)}")
    print(f"OK: {name} unloaded" if proc.returncode == 0 else f"note: {name} was not loaded")
    plist_path = plist_path_for(name)
    if plist_path.exists():
        plist_path.unlink()
        print(f"OK: removed {plist_path}")


def installed_names() -> list[str]:
    if not LAUNCH_AGENTS_DIR.is_dir():
        return []
    return sorted(p.name[len(LABEL_PREFIX) : -len(".plist")] for p in LAUNCH_AGENTS_DIR.glob(f"{LABEL_PREFIX}*.plist"))


def agent_state(name: str) -> str:
    proc = launchctl("print", f"{domain()}/{label_for(name)}")
    if proc.returncode != 0:
        return "not loaded"
    state = last_exit = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("state = "):
            state = line.split("=", 1)[1].strip()
        elif line.startswith("last exit code = "):
            last_exit = line.split("=", 1)[1].strip()
    return f"loaded, {state or 'unknown state'}, last exit {last_exit or 'n/a (never ran)'}"


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_list(jobs: list[dict]) -> int:
    if not jobs:
        print("no jobs declared")
    for job in jobs:
        flag = "" if job["enabled"] else "  [disabled]"
        print(f"{job['name']}{flag}")
        print(f"    when:    {describe_schedule(job['schedule'])}")
        print(f"    command: {job['command']}")
        if job.get("description"):
            print(f"    about:   {job['description']}")
    return 0


def cmd_install(jobs: list[dict], names: list[str]) -> int:
    chosen = select(jobs, names)
    ok = True
    for job in chosen:
        if not job["enabled"]:
            # An explicitly named disabled job is still skipped: flip the flag instead.
            print(f"SKIP: {job['name']} is disabled in the descriptor")
            if job["name"] in installed_names():
                uninstall_job(job["name"])
            continue
        ok &= install_job(job)

    if not names:
        # Full sync: drop agents whose job left the descriptor.
        declared = {j["name"] for j in jobs}
        for stale in installed_names():
            if stale not in declared:
                print(f"note: {stale} is no longer in the descriptor")
                uninstall_job(stale)
    return 0 if ok else 1


def cmd_uninstall(names: list[str]) -> int:
    targets = names or installed_names()
    if not targets:
        print("note: no scheduled-job agents installed")
    for name in targets:
        uninstall_job(name)
    return 0


def cmd_status(jobs: list[dict]) -> int:
    names = sorted({j["name"] for j in jobs} | set(installed_names()))
    if not names:
        print("no jobs declared or installed")
    by_name = {j["name"]: j for j in jobs}
    for name in names:
        job = by_name.get(name)
        print(name)
        print(f"    agent: {agent_state(name)}")
        if job:
            print(f"    when:  {describe_schedule(job['schedule'])}" + ("" if job["enabled"] else "  [disabled]"))
        else:
            print("    WARN: installed but not in the descriptor -- run jobs-install to remove it")
        log = log_path_for(name)
        print(f"    log:   {log}" + ("" if log.exists() else " (not written yet)"))
    return 0


def cmd_run(name: str) -> int:
    proc = launchctl("kickstart", f"{domain()}/{label_for(name)}")
    if proc.returncode != 0:
        die(f"kickstart failed (is it installed?): {(proc.stderr or proc.stdout).strip()}")
    print(f"OK: started {name}; follow with: tail -f {log_path_for(name)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="Show jobs declared in the descriptor")
    mode.add_argument("--install", nargs="*", metavar="NAME", help="Write and load agents (no NAME: sync all)")
    mode.add_argument("--uninstall", nargs="*", metavar="NAME", help="Unload and remove agents (no NAME: all ours)")
    mode.add_argument("--status", action="store_true", help="Show agent state for every known job")
    mode.add_argument("--run", metavar="NAME", help="Run an installed job right now")
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=None,
        help="Descriptor path (default: $LINUXENV_DIR/config/scheduled-jobs.json)",
    )
    args = parser.parse_args()

    if sys.platform != "darwin":
        die("launchd is macOS-only")

    if args.uninstall is not None:
        return cmd_uninstall(args.uninstall)
    if args.run:
        return cmd_run(args.run)

    jobs = load_jobs(args.file or default_descriptor())
    if args.list:
        return cmd_list(jobs)
    if args.install is not None:
        return cmd_install(jobs, args.install)
    return cmd_status(jobs)


if __name__ == "__main__":
    sys.exit(main())
