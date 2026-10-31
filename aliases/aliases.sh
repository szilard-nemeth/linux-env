#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd $DIR

## LINUX-ENV ALIASES
alias linuxenv-reload="cp ~/development/my-repos/linux-env/setup-env.sh ~/.linuxenv/setup-env.sh && cp ~/development/my-repos/linux-env/.zshrc ~/ && LINUXENV_SKIP_COPY=0 LINUXENV_FORCE_COPY=1 LINUXENV_DEBUG=1 source ~/.linuxenv/setup-env.sh"
alias linuxenv-todos="grep '#TODO' -r $LINUX_ENV_REPO"
alias linuxenv-debug-on="echo \"enabled\" > ${ENV_DEBUG_SETUP_FILE}"
alias linuxenv-debug-off="echo \"disabled\" > ${ENV_DEBUG_SETUP_FILE}"
alias edit-linuxenv="subl ~/development/my-repos/linux-env/"
alias edit-run-configs="subl ~/development/my-repos/project-run-configurations/"
alias edit-branchcomparator-latest="subl ~/snemeth-dev-projects/yarn_dev_tools/latest-session-branchcomparator/"

## KNOWLEDGE BASE
alias edit-kb="subl ~/development/my-repos/knowledge-base"
alias edit-kb-private="subl ~/development/my-repos/knowledge-base-private"


## GOTO ALIASES
alias goto-linuxenv-repo="cd $LINUX_ENV_REPO"
alias goto-kb-public="cd $KB_REPO"
alias goto-kb-private="cd $KB_PRIVATE_REPO"
alias goto-pythoncommons="cd $PYTHON_COMMONS_REPO"
alias goto-yarndevtools="cd $YARNDEVTOOLS_REPO"


## GIT ALIASES
alias git-commits-above-master="git log --oneline HEAD ^master | wc -l"
alias git-mybranches="git branch | grep 'own-'"
alias git-commit-msg="git log -n 1 --pretty=format:%s"
alias git-remove-trailing-ws="git diff-tree --no-commit-id --name-only -r HEAD | xargs sed -i 's/[[:space:]]*$//'"
alias git-fix-author-info-private="git config user.email 'szilard.nemeth88@gmail.com' && git config user.name 'Szilard Nemeth' && git commit --amend --reset-author"
alias git-fix-author-info-cloudera="git config user.email 'snemeth@cloudera.com' && git config user.name 'Szilard Nemeth' && git commit --amend --reset-author"
alias git-add-all-tracked="git status -s | grep -v \"??\" | cut -c 4- | xargs git add"
alias git-merge-preview-simple="git merge-tree --write-tree --name-only HEAD"


#https://stackoverflow.com/a/40884093/1106893 --> 4b825dc642cb6eb9a060e54bf8d69288fbee4904 is the id of the "empty tree"
alias git-save-all-commits="rm /tmp/patches/*; git format-patch 4b825dc642cb6eb9a060e54bf8d69288fbee4904..HEAD -o /tmp/patches"
alias git-add-mod="git ls-files --modified | xargs git add"
alias gs="git status"
alias gc="git commit"
alias ga="git add"

## OTHER ALIASES
alias rm='safe-rm'
alias currentweek="date +%V"
alias vpn-szyszy="sudo openvpn --client --config ~/openvpn-szyszy/client.ovpn --ca ~/openvpn-szyszy/ca.crt"
alias date-formatted="date +%Y%m%d_%H%M%S"
alias sl="sl --help" # steam-locomotive: https://www.cyberciti.biz/tips/displays-animations-when-accidentally-you-type-sl-instead-of-ls.html
alias grep='grep --color=auto'
alias dfh='df -h'
alias bashrc='vim ~/.bashrc'
alias logs="find /var/log -type f -exec file {} \; | grep 'text' | cut -d' ' -f1 | sed -e's/:$//g' | grep -v '[0-9]$' | xargs tail -f"
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

## ls ALIASES
# Bare `ls` is left as system ls (fast, script-safe, no icons/ANSI in
# pipelines). Interactive listings go through colorls so you get icons +
# per-filetype colors + dirs-first sorting.
#
# Flag notes:
#   -l   long format
#   -A   almost-all (like -a but hides . and ..; less noise than -a)
#   --sd sort directories before files
#   colorls has no -F equivalent — the Nerd Font icons already distinguish
#   dirs / executables / symlinks / etc. visually.
alias ll='colorls -lA --sd'
alias la='colorls -A --sd'
alias l='colorls --sd'

# `lc` kept for muscle memory; identical to `ll` now.
alias lc='colorls -lA --sd'

# colorls tab completion (upstream-recommended setup step).
#
# Upstream README suggests:
#   source $(dirname $(gem which colorls))/tab_complete.sh
#
# That resolves `gem which colorls` on every shell startup — two Ruby
# invocations, ~200-500ms of latency per shell. Cache the resolved path in a
# file (an env var does not help: new kitty tabs don't inherit a sibling
# shell's environment) and recompute it when the colorls executable changes
# (gem upgrade/reinstall) or the cached tab_complete.sh disappears.
function _print-colorls-tab-complete-source {
    local gem_path
    gem_path="$(gem which colorls 2>/dev/null)" || return 1
    [[ -f "$(dirname "$gem_path")/tab_complete.sh" ]] || return 1
    echo "[[ -f '$(dirname "$gem_path")/tab_complete.sh' ]] && source '$(dirname "$gem_path")/tab_complete.sh'"
}
if command -v colorls >/dev/null 2>&1 && command -v gem >/dev/null 2>&1; then
    linuxenv-cached-source colorls-tab-complete "$(command -v colorls)" _print-colorls-tab-complete-source
fi

##Aliases for my DEV projects
#Assuming venv is in googlechrometoolkit repo's root

# Google chrome toolkit aliases + Python setup
GCHROME_TOOLKIT_ROOT="$HOME/development/my-repos/google-chrome-toolkit/"
GCHROME_TOOLKIT_MODULE_ROOT="$GCHROME_TOOLKIT_ROOT/googlechrometoolkit/"
GCHROME_TOOLKIT_VENV="$GCHROME_TOOLKIT_ROOT/venv/"
BIN_PYTHON_GCHROME="$GCHROME_TOOLKIT_VENV/bin/python3"
local SETUP_PYENV="PYTHONPATH=$GCHROME_TOOLKIT_ROOT:$PYTHONPATH"
alias save-tabs-android="$SETUP_PYENV $BIN_PYTHON_GCHROME $GCHROME_TOOLKIT_MODULE_ROOT/save_open_tabs_android.py"
alias save-chrome-history-all="$SETUP_PYENV $BIN_PYTHON_GCHROME $GCHROME_TOOLKIT_MODULE_ROOT/main.py --search-db-files --export-mode all"

alias myrepos-sync="myrepos_syncer.py"
alias gpwh="git-push-with-hooks.sh"

## OTHER ALIASES
# Add an "alert" alias for long running commands.  Use like so:
# sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'
# 'thefuck --alias' starts python (~200ms), so cache its output until thefuck is upgraded
linuxenv-cached-source thefuck-alias "$(command -v thefuck)" thefuck --alias || eval $(thefuck --alias)
alias mc='LANG=en_EN.UTF-8 mc'

#TODO create alias: resync all changes from linuxenv repo (copies all files)
#TODO make this a function
alias zip-files="sudo find / -iname *1564501696813_0001_01_000001* -print0 | sudo tar -czvf backup-1564501696813_0001-20190730.tar.gz --null -T -"

#https://stackoverflow.com/a/49752003/1106893
alias zsh-printcolors="for code in {000..255}; do print -P -- "$code: %F{$code}Color%f"; done"
alias print-aliases-functions="print -rl -- ${(k)aliases} ${(k)functions} ${(k)parameters}"
alias print-functions="print -l ${(ok)functions}" # https://superuser.com/a/684256


###WHITESPACE PIPE TRICK: https://superuser.com/a/1503113
# SP  ' '  0x20 = · U+00B7 Middle Dot
# TAB '\t' 0x09 = ￫ U+FFEB Halfwidth Rightwards Arrow
# CR  '\r' 0x0D = § U+00A7 Section Sign (⏎ U+23CE also works fine)
# LF  '\n' 0x0A = ¶ U+00B6 Pilcrow Sign (was "Paragraph Sign")
alias whitespace="sed 's/ /·/g;s/\t/￫/g;s/\r/§/g;s/$/¶/g'"

alias copy-trello-checklist-script="cat ~/development/my-repos/knowledge-base/codesnippets/js-html-css/copy-trello-checklist-smartlinks.js | pbcopy"
alias copy-pushbullet-linksaver-script="cat ~/development/my-repos/knowledge-base/codesnippets/js-html-css/pushbullet-save-links.js | pbcopy"
alias svim='vim -u ~/.SpaceVim/vimrc'
alias link-to-project-run-configurations="ln -s ~/development/my-repos/project-run-configurations/pycharm/$PROJECT_TO_LINK/.run ./.run"

alias history="history 1 -1"
alias mgitst="mgitstatus --depth=10 -e"
alias mgitst-myrepos="cd ~/development/my-repos/;mgitst"
alias mgitst-cloudera="cd ~/development/cloudera/;mgitst"

# replace BSD sed with GNU sed
alias sed=gsed

# Pycharm diff
alias pdiff="pycharm diff"
alias git-diff-dir="git difftool --no-prompt"

# pdiff-unstaged — show unstaged changes (working tree vs index) in PyCharm.
# One directory argument: a single PyCharm directory diff of the index copy of that
# directory vs the real one, so the right side stays editable; untracked files show
# as right-only and deleted ones as left-only. Anything else (no args, several paths,
# globs): one diff window per file `git diff -- <pathspec>...` lists, skipping
# untracked and deleted files.
# The index side is written to a temp dir that is not cleaned up: the launcher returns
# before PyCharm has read it. Paths are absolute because the launcher goes through
# `open`, which does not keep the current directory.
# Usage: pdiff-unstaged [<pathspec>...]
#   pdiff-unstaged cloudera/tasks/cde/DEX-24419      # one directory diff window
#   pdiff-unstaged                                   # every unstaged file in this repo
#   pdiff-unstaged '*.md' notes/todo.md              # one window per file
function pdiff-unstaged {
  local top
  top="$(git rev-parse --show-toplevel)" || return
  local tmp
  tmp="$(mktemp -d -t pdiff-unstaged)" || return

  if [[ $# -eq 1 && -d "$1" ]]; then
    local rel abs
    rel="$(git -C "$1" rev-parse --show-prefix)" || return
    abs="$(cd "$1" && pwd)"
    git ls-files -z --full-name -- "$1" | git -C "$top" checkout-index -z --stdin --prefix="$tmp/"
    mkdir -p "$tmp/$rel"
    pycharm diff "$tmp/$rel" "$abs"
    return
  fi

  local f n=0
  while IFS= read -r -d '' f; do
    [[ -e "$top/$f" ]] || { echo "skip (deleted): $f" >&2; continue; }
    mkdir -p "$tmp/$(dirname "$f")"
    git -C "$top" show ":$f" > "$tmp/$f" || continue
    pycharm diff "$tmp/$f" "$top/$f"
    n=$((n + 1))
  done < <(git diff --name-only -z -- "$@")
  [[ $n -gt 0 ]] || echo "no unstaged changes${*:+ under $*}" >&2
}

alias md2html="python -m markdown"

# ---------------------------------------------------------------------------
# claude-sessions helpers — navigate exports written by claude-code-tools/export_claude_sessions.py
# into $CLAUDE_SESSIONS_DIR. The exporter sets each file's mtime to the last
# conversation-message timestamp, so mtime-desc == "most recent work first".
# ---------------------------------------------------------------------------

# List last N (default 15) claude-session project dirs by mtime desc, full paths.
# Usage: claude-sessions-recent [N]
function claude-sessions-recent {
  local n="${1:-15}"
  # BSD stat (macOS): '%m %N' = mtime-epoch + absolute path. Sort desc, strip mtime.
  find "$CLAUDE_SESSIONS_DIR" -mindepth 1 -maxdepth 1 -type d \
    -exec stat -f '%m %N' {} + \
    | sort -rn \
    | head -n "$n" \
    | awk '{ $1=""; sub(/^ /,""); print }'
}

# Interactive picker: numbered list of last N project dirs (basenames);
# cd into the chosen one. Enter 'q' to abort.
# Usage: claude-sessions-cd [N]
function claude-sessions-cd {
  local n="${1:-15}"
  local -a dirs
  local IFS=$'\n'
  dirs=($(claude-sessions-recent "$n"))
  if [[ ${#dirs[@]} -eq 0 ]]; then
    echo "no claude-session project dirs under $CLAUDE_SESSIONS_DIR" >&2
    return 1
  fi

  # Show basenames in the picker (full paths are long); cd by full path.
  local -a labels=()
  local d
  for d in "${dirs[@]}"; do labels+=("$(basename "$d")"); done

  PS3="pick a project (q to quit): "
  local label
  select label in "${labels[@]}"; do
    [[ "$REPLY" == "q" ]] && return 130
    if [[ -n "$label" ]]; then
      # $label is a basename directly under $CLAUDE_SESSIONS_DIR — cd via that,
      # not by indexing $dirs, because bash arrays are 0-based and zsh's are 1-based.
      cd "$CLAUDE_SESSIONS_DIR/$label"
      return
    fi
    echo "not a valid choice" >&2
  done
}

# kbc — commit ONLY the given paths in the private KB, from any directory.
# `git commit -- <paths>` ignores anything else that is staged, so session
# exports, DEX task files and learning notes never leak into each other's commits.
# Paths are relative to the KB root ($KB_PRIVATE_REPO). Quote globs so git
# expands them, not the shell (zsh fails with "no matches found" outside the KB).
#
# Usage: kbc "<message>" <path>...
#   kbc "Export Claude session markdown files" claude-sessions
#   kbc "DEX-25018: Record cluster evidence" 'cloudera/tasks/cde/DEX-22893/DEX-25018*'
#   kbc "Learnings: AWC auth and kind" cloudera/claude cloudera/cde/cde-awc
#   kbc "Learnings: Knox JWT" cloudera/cde/cde-awc/cde-awc-auth.md
#
# Preview what one area would commit: git -C "$KB_PRIVATE_REPO" status -- cloudera/tasks
function kbc {
  if [[ $# -lt 2 ]]; then
    echo 'usage: kbc "<message>" <path>...' >&2
    return 2
  fi
  local msg="$1"
  shift
  git -C "$KB_PRIVATE_REPO" add -A -- "$@" &&
    git -C "$KB_PRIVATE_REPO" commit -m "$msg" -- "$@"
}

# kbc-claude-sessions — commit everything under claude-sessions/ via kbc.
# Usage: kbc-claude-sessions ["<message>"]
#   kbc-claude-sessions
#   kbc-claude-sessions "Export Claude sessions after the DEX-25018 cluster test"
function kbc-claude-sessions {
  kbc "${1:-Export Claude session markdown files}" claude-sessions
}

# kbc-dex-task — commit a DEX task's directories under cloudera/tasks/ via kbc,
# as "<TICKET>: <message>". Matches dirs named exactly <TICKET> or <TICKET>-<slug>
# at any depth (task dirs nest under their epic), so DEX-1234 never picks up DEX-12345.
# A task dir nested inside it (e.g. a sub-ticket) is committed with it.
# Usage: kbc-dex-task DEX-1234 "<message>"
#   kbc-dex-task DEX-25018 "Record cluster evidence"
#     -> commits cloudera/tasks/cde/DEX-22893/DEX-25018-issues-identified-from-sr-verifications
#        as "DEX-25018: Record cluster evidence"
function kbc-dex-task {
  if [[ $# -ne 2 || ! "$1" =~ ^DEX-[0-9]+$ ]]; then
    echo 'usage: kbc-dex DEX-1234 "<message>"' >&2
    return 2
  fi
  local ticket="$1" msg="$2"
  local root="${KB_PRIVATE_REPO%/}/"
  local -a paths=()
  local p
  while IFS= read -r p; do
    paths+=("${p#"$root"}")
  done < <(find "${root}cloudera/tasks" -type d \( -name "$ticket" -o -name "$ticket-*" \) -prune)
  if [[ ${#paths[@]} -eq 0 ]]; then
    echo "no task dir for $ticket under ${root}cloudera/tasks" >&2
    return 1
  fi
  kbc "$ticket: $msg" "${paths[@]}"
}

function evernote-backup {
  evernote-backup init-db
  evernote-backup sync
  curr_date=$(date +%Y%m%d_%H%M%S)
  evernote-backup export /Users/snemeth/Downloads/evernote-backup-all-notes-$curr_date
}