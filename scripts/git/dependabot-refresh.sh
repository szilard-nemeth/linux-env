#!/usr/bin/env bash
#
# dependabot-refresh.sh
#
# Replaces the open Dependabot PRs of linux-env with a single lock refresh PR:
# `poetry update` moves every locked package to the newest version its
# pyproject.toml range allows, which also picks up security fixes Dependabot
# never opened a PR for. Once the PR is merged, Dependabot closes its own PRs
# as superseded.
#
# Steps: update master, create chore/security-dependency-updates-<date>,
# optionally raise direct dependency ranges, poetry update, pytest,
# pre-commit, then (after confirmation) commit, push and open the PR.
#
# Usage:
#   dependabot-refresh.sh [-y|--yes] [PKG@CONSTRAINT ...]
#
#   PKG@CONSTRAINT  direct dependency whose range blocks a fix, passed to
#                   `poetry add`, e.g. 'lxml@^6.1.0'. Check the Dependabot PRs
#                   that also touch pyproject.toml to find these.
#   -y, --yes       commit, push and open the PR without asking
#
# Repo location: $LINUXENV_DIR, else ~/development/my-repos/linux-env.

set -euo pipefail

BASE_BRANCH="master"
ASSUME_YES=0
CONSTRAINTS=()

for arg in "$@"; do
    case "$arg" in
        -y|--yes) ASSUME_YES=1 ;;
        -h|--help)
            sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        -*)
            echo "ERROR: unknown flag: $arg" >&2
            exit 2
            ;;
        *@*) CONSTRAINTS+=("$arg") ;;
        *)
            echo "ERROR: expected PKG@CONSTRAINT, got: $arg" >&2
            exit 2
            ;;
    esac
done

# setup-pythonpath leaks a newer site-packages into the poetry venv and breaks
# pytest / pre-commit there.
unset PYTHONPATH

REPO_DIR="${LINUXENV_DIR:-$HOME/development/my-repos/linux-env}"
cd "$REPO_DIR"

# --- safety checks -----------------------------------------------------------

for tool in git gh poetry; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool not found on PATH" >&2
        exit 1
    fi
done

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: working tree has uncommitted changes; commit or stash first" >&2
    exit 1
fi

branch="chore/security-dependency-updates-$(date +%Y%m%d)"
if git rev-parse --verify --quiet "refs/heads/$branch" >/dev/null; then
    echo "ERROR: branch $branch already exists; delete it or finish that run first" >&2
    exit 1
fi

# --- what is being replaced --------------------------------------------------

dependabot_prs=$(gh pr list --author "app/dependabot" --state open --limit 100 \
    --json number,title --jq '.[] | "#\(.number) \(.title)"')
if [[ -z "$dependabot_prs" ]]; then
    echo "OK: no open Dependabot PRs. Refreshing the lock anyway."
else
    echo "Open Dependabot PRs this refresh replaces:"
    echo "$dependabot_prs" | sed 's/^/  /'
fi
echo

# --- refresh -----------------------------------------------------------------

git switch "$BASE_BRANCH"
git pull --ff-only
git switch -c "$branch"

for spec in "${CONSTRAINTS[@]+"${CONSTRAINTS[@]}"}"; do
    echo "Raising range: poetry add '$spec'"
    poetry add "$spec"
done

poetry update

if git diff --quiet -- poetry.lock pyproject.toml; then
    echo "OK: poetry update changed nothing; removing $branch."
    git switch "$BASE_BRANCH"
    git branch -d "$branch"
    exit 0
fi

echo
git diff --stat -- poetry.lock pyproject.toml
echo

poetry run python -m pytest
poetry run pre-commit run --all-files

# --- commit, push, PR --------------------------------------------------------

if [[ "$ASSUME_YES" -ne 1 ]]; then
    read -r -p "Tests and pre-commit passed. Commit, push and open the PR? [y/N] " reply
    case "$reply" in
        y|Y|yes|YES) ;;
        *)
            echo "SKIP: left the changes uncommitted on $branch."
            exit 0
            ;;
    esac
fi

git add poetry.lock pyproject.toml
git commit -m "Update dependencies to clear Dependabot security alerts"
git push -u origin "$branch"

body="## What"
if [[ ${#CONSTRAINTS[@]} -gt 0 ]]; then
    body+=$'\n'"- Raised ranges: \`${CONSTRAINTS[*]}\`"
fi
body+=$'\n'"- \`poetry update\`: every locked package refreshed to the newest version its range allows"
body+=$'\n\n'"## Why"$'\n'"Replaces the open Dependabot PRs with one lock refresh. It also picks up security fixes Dependabot opened no PR for."
if [[ -n "$dependabot_prs" ]]; then
    body+=$'\n\n'"Supersedes:"$'\n'"$(echo "$dependabot_prs" | sed 's/^/- /')"
fi
body+=$'\n\n'"## Testing done"$'\n'"- \`poetry run python -m pytest\`"$'\n'"- \`pre-commit run --all-files\`"

gh pr create --base "$BASE_BRANCH" --head "$branch" \
    --title "Update locked dependencies to clear Dependabot security alerts" \
    --body "$body"

echo
echo "OK: PR opened. After it merges, Dependabot should close the superseded PRs within a day."
echo "Remaining alerts:"
echo "  gh api 'repos/{owner}/{repo}/dependabot/alerts?state=open' -q '.[].dependency.package.name' | sort | uniq -c"
echo "Alerts that stay open usually need a newer Python than pyproject.toml allows (python = \"^3.9\")."
