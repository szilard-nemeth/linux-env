# kitty session save & restore

Keeps your kitty layout (OS windows, tabs, splits, cwds, running commands) across
restarts, and archives what was on screen so you can read back context a restart
cannot recreate.

| Script | Purpose |
|---|---|
| `kitty_session_autosave.py` | launchd agent: keeps the session file fresh automatically |
| `kitty_save_session.py` | one-shot layout capture → session file |
| `kitty_snapshot_windows.py` | one-shot text capture → one file per window + `index.md` |
| `kitty_session_lib.py` | shared helpers (kitty access, rendering, atomic writes, backups) |

## Why the autosave exists

`kitty.conf` sets `startup_session sessions/restore.conf`, so every kitty launch
restores that one file. Nothing wrote it unless you remembered to run
`kitty-save-session` by hand — so it went stale and every restart faithfully
restored a weeks-old layout. The agent fixes that.

## Prerequisites (one-time)

1. `allow_remote_control yes` in `kitty.conf` — already set.
2. `listen_on unix:${HOME}/.config/kitty/kitty.sock` in `kitty.conf` — added by
   this change. **Required**: without it, remote control only works over the
   controlling terminal, so a background agent gets
   `open /dev/tty: device not configured` and can never reach kitty.
3. **Fully quit and relaunch kitty** (Cmd+Q, not just closing the window).
   `listen_on` is applied at startup only; reloading the config does not open
   the listener.

> Before that relaunch, save your current layout by hand — the relaunch restores
> whatever `restore.conf` currently holds, which may be old:
> ```bash
> kitty-save-session        # run from inside a kitty window
> ```

Verify afterwards:

```bash
echo "$KITTY_LISTEN_ON"      # unix:/Users/<you>/.config/kitty/kitty.sock-<pid>
kitty-session-targets        # lists live control sockets
```

Note that this socket grants full control of kitty — reading any window's
contents, running commands — to any process running as you. It lives in
`~/.config/kitty/` (mode 0700) rather than `/tmp` for that reason.

## Autosave

```bash
kitty-autosave-install      # write + load the LaunchAgent
kitty-autosave-status       # is it running? how fresh is the session?
kitty-autosave-uninstall    # stop + remove it
```

**When it saves**

- Every 60s — covers crashes, panics and power loss.
- Once more on SIGTERM, which launchd sends to user agents at logout/shutdown.
  That is the "saved right before reboot" case.

The periodic save is the primary mechanism; the shutdown save is a bonus. If
SIGTERM never arrives, you lose at most 60 seconds of layout changes.

**When it deliberately does *not* save.** An autosave firing every minute could
silently destroy the only copy of a good layout, so a write happens only when
it is clearly an improvement:

| Situation | Behaviour |
|---|---|
| kitty not running / unreachable | skip, keep the last good file |
| zero windows captured | skip |
| layout identical to what is on disk | skip (no churn, no wasted backup) |
| window count collapsed below half | skip up to 3 ticks, then accept |

The last one covers the boot race: just after a restart kitty is still replaying
the session, so a tick landing mid-restore would otherwise overwrite 13 windows
with 3. The 3-tick cap means deliberately closing most of your tabs still saves.

Writes are atomic (temp file in the same dir, fsync, then rename), so a kill
mid-write leaves the previous file intact rather than a truncated one.

Every 15 minutes it also captures per-window text with full scrollback, pruned
after 7 days or 2 GiB (whichever comes first); snapshots are ~1 MB each.
Text snapshots are skipped on the shutdown path — a full-scrollback capture can
outlast launchd's `ExitTimeOut`, and losing the layout save to it would defeat
the point.

## Manual use

```bash
kitty-save-session                 # layout -> ~/.config/kitty/sessions/restore.conf
kitty-save-session --stdout        # print, don't write
kitty-snapshot-windows --scrollback  # text of every window, incl. scrollback
kitty-save-all --scrollback        # both at once
```

`kitty-save-all` forwards its arguments to the **snapshot** script only. For
session-save options (`--no-restore-processes`, `-o OUT`) call
`kitty-save-session` directly.

## Reading a snapshot back

```bash
less ~/.config/kitty/snapshots/latest/index.md        # overview: tabs, cwds, processes
cat  ~/.config/kitty/snapshots/latest/os1-tab02-*.ansi  # exact text, with colours
grep -a -rn "ERROR" ~/.config/kitty/snapshots/latest/   # search across tabs
```

## Recovering an earlier session

```bash
kitty-session-age          # when was restore.conf written, and what did it hold
kitty-session-backups      # newest 50 previous versions
kitty --session ~/.config/kitty/sessions/backups/restore.<timestamp>.conf
```

To make a backup the one kitty restores from, copy it over `restore.conf`.

## Where things live

| Path | Contents |
|---|---|
| `~/.config/kitty/kitty.sock-<pid>` | kitty's control socket (one per instance) |
| `~/.config/kitty/sessions/restore.conf` | the file kitty restores from, mode 0600 |
| `~/.config/kitty/sessions/backups/` | previous versions, newest 50 |
| `~/.config/kitty/sessions/autosave.log` | agent log |
| `~/.config/kitty/sessions/.autosave-state.json` | snapshot schedule + guard counters |
| `~/.config/kitty/snapshots/<timestamp>/` | per-window text, `latest` symlinks to newest |
| `~/Library/LaunchAgents/com.snemeth.kitty-session-autosave.plist` | generated, not in the repo |

The session file carries a `#::` comment header recording when it was written
and how much it held. kitty's session parser ignores `#` lines, so it is inert
at restore time.

## Caveats

- **Running commands are re-launched on restore.** The captured argv is re-run
  verbatim, so be careful with non-idempotent commands (`docker run`,
  `kubectl apply`). `--no-restore-processes` disables this entirely.
- **In-memory state is lost.** nvim reopens the same files but loses unsaved
  buffers, undo and jump history; `less` reopens at the top; REPLs restart empty.
- **Some commands are never restored.** `DEFAULT_PROCESS_DENYLIST` in
  `kitty_session_lib.py` drops transient ones (`kitty @ …` one-shots,
  `caffeinate`). Add your own with `--process-denylist REGEX` (repeatable),
  which *replaces* the defaults. Worth knowing: long-running agents are **not**
  denied by default, so if several windows are running one, every kitty launch
  starts that many fresh sessions. To stop that:
  ```bash
  kitty-autosave-install --process-denylist '^claude\b'
  ```
- **Session files can contain secrets.** They record full command lines, which
  may include `--token=…`. Files are written mode 0600.
- **One focus point per session file.** kitty's session format can only express
  a single focused tab/window, so the tab you were on is restored, but other
  tabs' active split is not individually preserved.

## Troubleshooting

`kitty-autosave-status` answers most questions. Common cases:

- *kitty: NOT reachable* — `listen_on` isn't active yet; fully quit and relaunch
  kitty (step 3 above).
- *session over an hour old* — the agent isn't running; check
  `kitty-autosave-logs` and re-run `kitty-autosave-install`.
- *agent: loaded but not running* — look at the log; with `KeepAlive` set,
  launchd respawns it, so a repeating exit means a real error.

```bash
kitty-autosave-once     # run one cycle in the foreground and print the decision
kitty-autosave-logs     # tail the agent log
```
