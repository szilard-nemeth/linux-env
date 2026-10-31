#!/usr/bin/env bash

# Shell-startup output cache.
# Tools like 'thefuck --alias', 'kitty + complete setup zsh' or 'go env GOPATH' print the same init code
# on every shell launch, but each takes 100-500ms to start. Cache their output in a file and regenerate
# it only when the file it depends on (usually the tool's binary) is newer than the cache.
# Clear all caches with: linuxenv-cache-clear
# Sourced early by .zprofile / .zshrc (from ~/.linuxenv/scripts), so keep this file dependency-free.

LINUXENV_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/linuxenv"

# Usage: linuxenv-cached-source <cache-name> <dependency-file> <command> [args...]
# Sources the cached stdout of <command>, regenerating it if missing or older than <dependency-file>.
# <command> may be a shell function. Returns 1 (and caches nothing) if <command> fails.
function linuxenv-cached-source {
    local cache_file="$LINUXENV_CACHE_DIR/$1.sh" dep="$2"
    shift 2
    if [[ ! -s "$cache_file" || "$dep" -nt "$cache_file" ]]; then
        mkdir -p "$LINUXENV_CACHE_DIR"
        if ! "$@" > "$cache_file.tmp" 2>/dev/null; then
            rm -f "$cache_file.tmp"
            return 1
        fi
        mv "$cache_file.tmp" "$cache_file"
    fi
    . "$cache_file"
}

function linuxenv-cache-clear {
    rm -f "$LINUXENV_CACHE_DIR"/*.sh && echo "Cleared $LINUXENV_CACHE_DIR"
}
