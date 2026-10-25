alias kitty-copy-screen="kitty @ get-text --extent screen | kitty +kitten clipboard"
alias kitty-copy-last-command="kitty @ get-text --extent last_cmd_output | kitty +kitten clipboard"
alias kitty-copy-all="kitty @ get-text --extent all | kitty +kitten clipboard"
alias kitty-save-session="kitty_save_session.py"
alias kitty-snapshot-windows="kitty_snapshot_windows.py"

# Save everything in one shot: the restore session file AND a text snapshot
# of every window (screen + running command) in ~/.config/kitty/snapshots/.
# Use before a reboot to get both auto-restore and a visual memory aid.
# Any flags ("$@") are forwarded to the snapshot script (e.g. --scrollback,
# --plain, -o DIR); the session save runs with its defaults. For session
# tuning (--no-restore-processes, -o OUT) call `kitty-save-session` directly.
kitty-save-all() {
  kitty_save_session.py && kitty_snapshot_windows.py "$@"
}

# --- Session autosave (launchd agent) ------------------------------------
# Keeps ~/.config/kitty/sessions/restore.conf fresh so a Mac restart brings
# back the layout you actually had: every minute, plus a final save when
# launchd tears the agent down at logout/shutdown.
# Needs `listen_on` in kitty.conf and a full kitty relaunch -- see
# scripts/kitty/README.md.
alias kitty-autosave="kitty_session_autosave.py"
alias kitty-autosave-install="kitty_session_autosave.py --install"
alias kitty-autosave-uninstall="kitty_session_autosave.py --uninstall"
alias kitty-autosave-status="kitty_session_autosave.py --status"
# One save cycle in the foreground, for debugging the guards.
alias kitty-autosave-once="kitty_session_autosave.py --once"
alias kitty-session-targets="kitty_save_session.py --list-targets"

kitty-autosave-logs() {
  local log="$HOME/.config/kitty/sessions/autosave.log"
  [[ -f $log ]] || { echo "no autosave log yet at $log" >&2; return 1; }
  tail -f "$log"
}

# How stale is the session kitty would restore from right now?
kitty-session-age() {
  local f="$HOME/.config/kitty/sessions/restore.conf"
  [[ -f $f ]] || { echo "no session file at $f" >&2; return 1; }
  grep '^#:: ' "$f" | sed 's/^#:: /  /'
  print -- "  mtime: $(date -r "$f" '+%Y-%m-%d %H:%M:%S')"
}

# Previous session files, newest first. Restore one with:
#   kitty --session ~/.config/kitty/sessions/backups/<file>
kitty-session-backups() {
  local d="$HOME/.config/kitty/sessions/backups"
  [[ -d $d ]] || { echo "no backups yet at $d" >&2; return 1; }
  ls -lt "$d" | head -20
}
# alias kitty-shortcuts='/Applications/kitty.app/Contents/MacOS/kitty --debug-config 2>&1 | grep -E "^(map|mouse_map) " | sort | less'

kitty-shortcuts() {
  local conf="${KITTY_CONFIG_DIRECTORY:-$HOME/.config/kitty}/kitty.conf"
  [[ -f $conf ]] || { echo "no kitty.conf at $conf" >&2; return 1; }
  # Follow `include` lines one level deep, then grep map/mouse_map
  {
    print -- "# $conf"
    grep -E '^(map|mouse_map) ' "$conf"
    grep -E '^include ' "$conf" | awk '{print $2}' | while read -r inc; do
      [[ $inc = /* ]] || inc="$(dirname "$conf")/$inc"
      [[ -f $inc ]] || continue
      print -- "\n# $inc"
      grep -E '^(map|mouse_map) ' "$inc"
    done
  } | less
}
