#!/usr/bin/env bash
#
# git-strip-claude-trailers.sh
#
# Rewrites every commit on the current branch (from the merge-base with a base
# branch up to HEAD) and removes Claude Code trailers from each commit message:
#
#   Co-Authored-By: Claude <noreply@anthropic.com>   (case-insensitive)
#   <robot-emoji> Generated with [Claude Code](...)
#   ...any line containing "Generated with [Claude Code]"
#
# Trailing blank lines left behind by the strip are collapsed.
#
# Usage:
#   git-strip-claude-trailers.sh [base-branch] [-y|--yes]
#
# Defaults:
#   base-branch = master
#
# Wired up as `git strip-claude` via ~/.gitconfig.

set -euo pipefail

BASE_BRANCH="master"
ASSUME_YES=0

for arg in "$@"; do
    case "$arg" in
        -y|--yes) ASSUME_YES=1 ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        -*)
            echo "ERROR: unknown flag: $arg" >&2
            exit 2
            ;;
        *) BASE_BRANCH="$arg" ;;
    esac
done

# --- safety checks -----------------------------------------------------------

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: not inside a git working tree" >&2
    exit 1
fi

current_branch=$(git symbolic-ref --short HEAD 2>/dev/null || true)
if [[ -z "$current_branch" ]]; then
    echo "ERROR: HEAD is detached; refusing to rewrite" >&2
    exit 1
fi

if [[ "$current_branch" == "$BASE_BRANCH" ]]; then
    echo "ERROR: current branch is the base branch ($BASE_BRANCH); refusing to rewrite" >&2
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: working tree has uncommitted changes; commit or stash first" >&2
    exit 1
fi

# Resolve base ref: prefer origin/<base> if it exists (more accurate merge-base
# when local <base> is stale), otherwise local.
if git rev-parse --verify --quiet "origin/${BASE_BRANCH}" >/dev/null; then
    base_ref="origin/${BASE_BRANCH}"
elif git rev-parse --verify --quiet "$BASE_BRANCH" >/dev/null; then
    base_ref="$BASE_BRANCH"
else
    echo "ERROR: base branch not found locally or on origin: $BASE_BRANCH" >&2
    exit 1
fi

merge_base=$(git merge-base HEAD "$base_ref")
head_sha=$(git rev-parse HEAD)

if [[ "$merge_base" == "$head_sha" ]]; then
    echo "OK: no commits on $current_branch beyond $base_ref; nothing to do."
    exit 0
fi

commit_count=$(git rev-list --count "${merge_base}..HEAD")

echo "Base branch:      $base_ref"
echo "Merge-base:       $merge_base"
echo "Current branch:   $current_branch @ $head_sha"
echo "Commits to rewrite: $commit_count"
echo
echo "Commits:"
git log --oneline "${merge_base}..HEAD"
echo

if [[ "$ASSUME_YES" -ne 1 ]]; then
    read -r -p "Rewrite these $commit_count commit(s) to strip Claude trailers? [y/N] " reply
    case "$reply" in
        y|Y|yes|YES) ;;
        *) echo "SKIP: aborted by user."; exit 0 ;;
    esac
fi

# --- do the rewrite ----------------------------------------------------------

# The filter reads a commit message on stdin and writes the rewritten one to
# stdout. sed drops the Claude trailer lines; awk then removes any trailing
# blank lines the deletion left behind.
export FILTER_BRANCH_SQUELCH_WARNING=1

git filter-branch -f --msg-filter '
    sed -E \
        -e "/^[Cc]o-[Aa]uthored-[Bb]y:[[:space:]]*Claude/d" \
        -e "/Generated with \[Claude Code\]/d" \
    | awk "{ lines[NR] = \$0 }
           END {
               n = NR
               while (n > 0 && lines[n] == \"\") n--
               for (i = 1; i <= n; i++) print lines[i]
           }"
' "${merge_base}..HEAD"

echo
echo "OK: rewrote $commit_count commit(s) on $current_branch."
echo "Note: filter-branch left refs/original/ backups; drop them with:"
echo "  git update-ref -d refs/original/refs/heads/$current_branch"
echo "If the branch is already pushed, you will need: git push --force-with-lease"
