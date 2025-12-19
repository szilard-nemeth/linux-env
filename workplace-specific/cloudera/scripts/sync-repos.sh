#!/usr/bin/env bash

# BASED ON THIS ANSWER: https://github.community/t5/How-to-use-Git-and-GitHub/Adding-a-folder-from-one-repo-to-another/m-p/5574#M1817

function sync-yarndevtools-repo {
  # Define your constants here
  SOURCE_URL="https://github.com/szilard-nemeth/yarn-dev-tools.git"
  MIRROR_URL="https://github.infra.cloudera.com/snemeth/yarn-dev-tools-mirror.git"

  # Default branch to master if no argument is provided
  SYNC_BRANCH=${1:-"master"}
  TARGET_BRANCH=${2:-"master"}

  echo "Initiating sync for branch: $SYNC_BRANCH"

  # Invoke the Python script
  # --force is added here to make it non-interactive
  python3 "$HOME_LINUXENV_DIR"/scripts/git/git_repo_mirror.py \
      --source "$SOURCE_URL" \
      --mirror "$MIRROR_URL" \
      --source-branch "$SYNC_BRANCH" \
      --target-branch "$TARGET_BRANCH" \
      --force

  echo "Exit code of $HOME_LINUXENV_DIR/scripts/git/git_repo_mirror.py: $?"
}

function sync-linux-env-repo {
  # Define your constants here
    SOURCE_URL="git@github.com:szilard-nemeth/linux-env.git"
    MIRROR_URL="git@github.infra.cloudera.com:snemeth/linux-env-mirror.git"

    # Default branch to master if no argument is provided
    SYNC_BRANCH=${1:-"master"}
    TARGET_BRANCH=${2:-"master"}

    echo "Initiating sync for branch: $SYNC_BRANCH"

    # Invoke the Python script
    # --force is added here to make it non-interactive
    python3 "$HOME_LINUXENV_DIR"/scripts/git/git_repo_mirror.py \
        --source "$SOURCE_URL" \
        --mirror "$MIRROR_URL" \
        --source-branch "$SYNC_BRANCH" \
        --target-branch "$TARGET_BRANCH" \
        --force

    echo "Exit code of $HOME_LINUXENV_DIR/scripts/git/git_repo_mirror.py: $?"
}
