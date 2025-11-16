#!/usr/bin/env bash

############################################
# CONFIGURATION — EDIT THESE
############################################
V_USER="szilard-nemeth"
SOURCE_REPO_SSH="git@github.com:$V_USER/backup-manager.git"
SUBDIR_PATH="modules/trello-backup"
NEW_REPO_SSH="git@github.com:$V_USER/trello-backup.git"
WORKDIR="/tmp/extract-$(date +%s)"
############################################

set -e

echo "🔧 Checking prerequisites..."
if ! command -v git >/dev/null; then
  echo "❌ git is not installed"; exit 1
fi
if ! command -v git-filter-repo >/dev/null; then
  echo "❌ git-filter-repo missing. Install via:"
  echo "   brew install git-filter-repo      # macOS"
  echo "   pip install git-filter-repo       # Linux/Windows"
  exit 1
fi

echo "📁 Working directory: $WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "⬇️ Cloning source repository..."
git clone "$SOURCE_REPO_SSH" source-repo
cd source-repo

echo "🔍 Verifying subdirectory exists..."
if [ ! -d "$SUBDIR_PATH" ]; then
  echo "❌ Subdirectory not found: $SUBDIR_PATH"; exit 1
fi

echo "✂️ Extracting history of subdirectory: $SUBDIR_PATH"
git filter-repo --path "$SUBDIR_PATH" --force

echo "Showing git log..."
git --no-pager log --oneline


echo "🌲 Configuring new remote repo..."
git remote remove origin || true
git remote add origin "$NEW_REPO_SSH"

echo "🚀 Pushing extracted repository to new repo..."
set -x
git push -u origin master
set +x



echo "🧹 Cleaning up original repository: removing subdirectory"
cd "$SOURCE_REPO_LOCAL_PATH"
git checkout "$SOURCE_BRANCH"
git pull

if [ ! -d "$SUBDIR_PATH" ]; then
  echo "⚠️ Directory already removed; cleanup skip"
else
  git rm -r "$SUBDIR_PATH"
  git commit -m "Move $SUBDIR_PATH to new repository ($NEW_REPO_SSH)"
  git push
  echo "✔️ Cleanup pushed to original repository"
fi

echo
echo "🎉 COMPLETED SUCCESSFULLY"
echo "➡️ New repo now contains only $SUBDIR_PATH (full history preserved)"
echo "➡️ Original repo no longer contains $SUBDIR_PATH"
echo "Work directory kept at: $WORKDIR"
