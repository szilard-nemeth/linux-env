#!/usr/bin/env bash

############################################
# CONFIGURATION — EDIT THESE
############################################
V_USER="szilard-nemeth"
SOURCE_REPO_SSH="git@github.com:$V_USER/backup-manager.git"
SOURCE_BRANCH="master"
SUBDIR_PATH="modules/trello-backup"
NEW_REPO_SSH="git@github.com:$V_USER/trello-backup.git"
WORKDIR="/tmp/extract-$(date +%s)"

SOURCE_REPO_LOCAL_PATH="$HOME/development/my-repos/backup-manager"
############################################

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "🧪 DRY RUN MODE ENABLED — no changes will be pushed or committed"
fi

set -e

msg() {
  echo -e "$1"
  sleep 0.05
}

msg "🔧 Checking prerequisites..."
command -v git >/dev/null || { echo "❌ git missing"; exit 1; }
command -v git-filter-repo >/dev/null || { echo "❌ git-filter-repo missing"; exit 1; }

msg "📁 Working directory: $WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

msg "⬇️ Cloning source repository..."
git clone --branch "$SOURCE_BRANCH" "$SOURCE_REPO_SSH" source-repo
cd source-repo

msg "🔍 Validating subdirectory exists..."
[[ -d "$SUBDIR_PATH" ]] || { echo "❌ Subdirectory not found: $SUBDIR_PATH"; exit 1; }

msg "✂️ Preparing to extract commit history related to: $SUBDIR_PATH"
if $DRY_RUN; then
  msg "🧪 DRY RUN: Would run: git filter-repo --path \"$SUBDIR_PATH\" --force"
else
  git filter-repo --path "$SUBDIR_PATH" --force
fi

msg "🌲 Preparing to push to new repository: $NEW_REPO_SSH"
if $DRY_RUN; then
  msg "🧪 DRY RUN: Would set new origin & push extracted repo"
else
  git remote remove origin || true
  git remote add origin "$NEW_REPO_SSH"
  git push -u origin "$SOURCE_BRANCH"
fi

msg "🧹 Preparing cleanup in original repository"
cd "$SOURCE_REPO_LOCAL_PATH"
git checkout "$SOURCE_BRANCH"
git pull

if [[ ! -d "$SUBDIR_PATH" ]]; then
  msg "⚠️ Directory already removed — skip cleanup"
else
  if $DRY_RUN; then
    msg "🧪 DRY RUN: Would run:"
    msg "    git rm -r \"$SUBDIR_PATH\""
    msg "    git commit -m \"Move $SUBDIR_PATH to new repository ($NEW_REPO_SSH)\""
    msg "    git push"
else
  git rm -r "$SUBDIR_PATH"
  git commit -m "Move $SUBDIR_PATH to new repository ($NEW_REPO_SSH)"
  git push
  msg "✔️ Cleanup committed & pushed"
  fi
fi

echo
if $DRY_RUN; then
  echo "🎉 DRY RUN COMPLETE — No modifications made."
  echo "🧪 Re-run without --dry-run to execute the extraction."
else
  echo "🎉 COMPLETED SUCCESSFULLY"
  echo "➡️ New repo now contains only $SUBDIR_PATH (history preserved)"
  echo "➡️ Original repo cleaned up"
fi
echo "Work directory: $WORKDIR"
