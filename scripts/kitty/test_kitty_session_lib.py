#!/usr/bin/env python3
"""Tests for kitty_session_lib.

Pure logic only -- nothing here needs a running kitty, so these also run on the
Linux CI box. The focus-emission and change-detection tests are regression
tests for two bugs that silently produce a wrong restore.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import kitty_session_lib as ksl  # noqa: E402


def window(wid: int, *, active: bool, focused: bool, cmd=None, cwd="/tmp") -> dict:
    return {
        "id": wid,
        "cwd": cwd,
        "title": "",
        "is_active": active,
        "is_focused": focused,
        "foreground_processes": [{"cmdline": cmd or ["/bin/zsh"]}],
    }


def tab(windows, *, title="t", focused=False, active=False, layout="stack") -> dict:
    return {
        "title": title,
        "layout": layout,
        "is_focused": focused,
        "is_active": active,
        "windows": windows,
    }


def focus_line_indexes(content: str) -> list[int]:
    return [i for i, line in enumerate(content.splitlines()) if line == "focus"]


# --------------------------------------------------------------------------
# focus emission (regression: restore always landed on the last tab)
# --------------------------------------------------------------------------


def three_tab_layout() -> list[dict]:
    """Mirrors how kitty actually reports focus.

    tabs.py marks is_focused on the active window of *every* tab in the focused
    OS window, so all three tabs below have a focused window; only tab index 1
    is the genuinely focused tab.
    """
    return [
        {
            "tabs": [
                tab([window(1, active=True, focused=True)], title="first"),
                tab(
                    [window(2, active=False, focused=False), window(3, active=True, focused=True)],
                    title="second",
                    focused=True,
                    active=True,
                ),
                tab([window(4, active=True, focused=True)], title="third"),
            ]
        }
    ]


def test_exactly_one_focus_is_emitted():
    content = ksl.render_session(three_tab_layout(), restore_processes=True, header=False)
    assert len(focus_line_indexes(content)) == 1, content


def test_focus_lands_in_the_focused_tab_not_the_last():
    content = ksl.render_session(three_tab_layout(), restore_processes=True, header=False)
    lines = content.splitlines()
    focus_idx = focus_line_indexes(content)[0]
    # The nearest preceding new_tab must be the focused one. kitty's `focus`
    # applies to the tab under construction, so position is what selects it.
    preceding = [line for line in lines[:focus_idx] if line.startswith("new_tab")]
    assert preceding[-1] == "new_tab second"


def test_focus_falls_back_to_active_tab_when_nothing_is_os_focused():
    data = [
        {
            "tabs": [
                tab([window(1, active=True, focused=False)], title="a"),
                tab([window(2, active=True, focused=False)], title="b", active=True),
            ]
        }
    ]
    content = ksl.render_session(data, restore_processes=True, header=False)
    lines = content.splitlines()
    focus_idx = focus_line_indexes(content)[0]
    assert [line for line in lines[:focus_idx] if line.startswith("new_tab")][-1] == "new_tab b"


def test_focus_os_window_only_when_several_os_windows():
    single = ksl.render_session(three_tab_layout(), restore_processes=True, header=False)
    assert "focus_os_window" not in single

    multi = three_tab_layout() + [{"tabs": [tab([window(9, active=True, focused=False)], title="other")]}]
    content = ksl.render_session(multi, restore_processes=True, header=False)
    assert content.count("focus_os_window") == 1
    # It must mark the first OS window, which owns the focused tab.
    assert content.index("focus_os_window") < content.index("new_os_window")


# --------------------------------------------------------------------------
# process capture
# --------------------------------------------------------------------------


def test_login_shell_is_not_relaunched():
    w = window(1, active=True, focused=True, cmd=["-zsh"])
    assert ksl.foreground_command(w) is None


def test_real_process_is_captured_with_argv():
    w = window(1, active=True, focused=True, cmd=["/usr/bin/nvim", "a b.txt"])
    assert ksl.foreground_command(w) == ["/usr/bin/nvim", "a b.txt"]


def test_default_denylist_drops_transient_commands():
    assert ksl.foreground_command(window(1, active=True, focused=True, cmd=["caffeinate", "-i", "-t", "300"])) is None
    assert ksl.foreground_command(window(2, active=True, focused=True, cmd=["kitten", "@", "ls"])) is None


def test_denylist_matches_absolute_paths_as_kitty_reports_them():
    """kitty reports argv[0] as an absolute path, which must still match."""
    w = window(1, active=True, focused=True, cmd=["/Applications/kitty.app/Contents/MacOS/kitten", "@", "ls"])
    assert ksl.foreground_command(w) is None
    w = window(2, active=True, focused=True, cmd=["/usr/bin/caffeinate", "-i", "-t", "300"])
    assert ksl.foreground_command(w) is None


def test_custom_denylist_replaces_default():
    w = window(1, active=True, focused=True, cmd=["claude"])
    assert ksl.foreground_command(w) == ["claude"]  # not denied by default
    deny = ksl.compile_denylist([r"^claude\b"])
    assert ksl.foreground_command(w, deny) is None
    # ...and by basename when kitty gives a full path.
    full = window(2, active=True, focused=True, cmd=["/opt/homebrew/bin/claude", "--resume"])
    assert ksl.foreground_command(full, deny) is None


def test_argv_is_shell_quoted():
    data = [{"tabs": [tab([window(1, active=True, focused=True, cmd=["nvim", "my file.txt"], cwd="/tmp/a b")])]}]
    content = ksl.render_session(data, restore_processes=True, header=False)
    assert "cd '/tmp/a b'" in content
    assert "launch nvim 'my file.txt'" in content


def test_no_restore_processes_emits_bare_launch():
    data = [{"tabs": [tab([window(1, active=True, focused=True, cmd=["nvim", "x"])])]}]
    content = ksl.render_session(data, restore_processes=False, header=False)
    assert "nvim" not in content
    assert "launch" in content


# --------------------------------------------------------------------------
# header / change detection (regression: header made every render differ)
# --------------------------------------------------------------------------


def test_header_is_comment_only_so_kitty_ignores_it():
    content = ksl.render_session(three_tab_layout(), restore_processes=True, header=True)
    header_lines = [line for line in content.splitlines() if line.startswith(ksl.HEADER_PREFIX)]
    assert header_lines
    # kitty's parser skips lines starting with '#'; anything else would execute.
    assert all(line.startswith("#") for line in header_lines)


def test_parse_header_reads_counts_back():
    content = ksl.render_session(three_tab_layout(), restore_processes=True, header=True)
    header = ksl.parse_header(content)
    assert ksl.header_int(header, "windows") == 4
    assert ksl.header_int(header, "tabs") == 3
    assert ksl.header_int(header, "os_windows") == 1
    assert "saved_at" in header


def test_strip_header_makes_identical_layouts_compare_equal():
    body = "new_tab a\nlaunch\n"
    first = f"{ksl.HEADER_PREFIX}saved_at: 2026-10-03T10:00:00\n\n{body}"
    second = f"{ksl.HEADER_PREFIX}saved_at: 2026-10-03T23:59:59\n{ksl.HEADER_PREFIX}windows: 1\n\n{body}"
    assert ksl.strip_header(first) == ksl.strip_header(second)


def test_strip_header_keeps_the_body():
    content = ksl.render_session(three_tab_layout(), restore_processes=True, header=True)
    assert ksl.strip_header(content).startswith("new_tab first")


def test_parse_header_tolerates_a_file_without_one():
    assert ksl.parse_header("new_tab a\nlaunch\n") == {}


# --------------------------------------------------------------------------
# durable writes
# --------------------------------------------------------------------------


def test_atomic_write_creates_file_with_private_mode(tmp_path):
    target = tmp_path / "restore.conf"
    ksl.atomic_write(target, "body\n")
    assert target.read_text() == "body\n"
    # Session files can contain tokens in captured argv.
    assert oct(target.stat().st_mode)[-3:] == "600"


def test_atomic_write_leaves_no_temp_residue(tmp_path):
    target = tmp_path / "restore.conf"
    ksl.atomic_write(target, "body\n")
    assert [p.name for p in tmp_path.iterdir()] == ["restore.conf"]


def test_failed_write_leaves_previous_file_untouched(tmp_path, monkeypatch):
    target = tmp_path / "restore.conf"
    ksl.atomic_write(target, "good\n")

    def boom(*_a, **_kw):
        raise OSError("disk full")

    monkeypatch.setattr(ksl.os, "replace", boom)
    with pytest.raises(OSError):
        ksl.atomic_write(target, "bad\n")

    assert target.read_text() == "good\n"
    # ...and the temp file was cleaned up rather than left behind.
    assert [p.name for p in tmp_path.iterdir()] == ["restore.conf"]


def test_rotate_backup_copies_then_prunes_to_keep(tmp_path):
    target = tmp_path / "restore.conf"
    ksl.atomic_write(target, "v0\n")

    for i in range(5):
        ksl.rotate_backup(target, keep=3)
        ksl.atomic_write(target, f"v{i + 1}\n")

    backups = sorted(ksl.backup_dir_for(target).glob("restore.*.conf"))
    assert len(backups) == 3
    assert target.read_text() == "v5\n"


def test_rotate_backup_is_a_noop_without_an_existing_file(tmp_path):
    assert ksl.rotate_backup(tmp_path / "missing.conf") is None


def test_backups_keep_the_private_mode(tmp_path):
    target = tmp_path / "restore.conf"
    ksl.atomic_write(target, "secret --token=abc\n")
    backup = ksl.rotate_backup(target)
    assert oct(backup.stat().st_mode)[-3:] == "600"


# --------------------------------------------------------------------------
# socket discovery
# --------------------------------------------------------------------------


def test_pid_alive_for_self_and_dead_for_unused():
    assert ksl._pid_alive(os.getpid()) is True
    # PID 0 is never a normal user process; os.kill(0, 0) signals our own
    # group, so use an implausibly high one instead.
    assert ksl._pid_alive(4_194_303) is False


def test_discover_sockets_ignores_plain_files_and_dead_pids(tmp_path, monkeypatch):
    monkeypatch.setattr(ksl, "SOCKET_BASE", tmp_path / "kitty.sock")
    # A regular file that looks like a socket name must not be offered.
    (tmp_path / f"kitty.sock-{os.getpid()}").write_text("not a socket")
    assert ksl.discover_sockets() == []


def test_counts_and_summary():
    data = three_tab_layout()
    assert ksl.count_windows(data) == 4
    assert ksl.counts(data) == {"os_windows": 1, "tabs": 3, "windows": 4}
    assert "3 tab(s)" in ksl.summarize(data, restore_processes=True)


def test_human_age_and_bytes():
    assert ksl.human_age(5) == "5s"
    assert ksl.human_age(125).startswith("2m")
    assert ksl.human_age(7200).startswith("2h")
    assert ksl.human_bytes(512) == "512 B"
    assert ksl.human_bytes(2048) == "2.0 KiB"
