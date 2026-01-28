#!/usr/bin/env bash

# BASED ON THIS ANSWER: https://github.community/t5/How-to-use-Git-and-GitHub/Adding-a-folder-from-one-repo-to-another/m-p/5574#M1817

function sync-yarndevtools-repo {
  echo "Initiating sync for branch: $SYNC_BRANCH"

  # Invoke the Python script
  # --force is added here to make it non-interactive
  python3 "$HOME_LINUXENV_DIR"/scripts/git/git_repo_mirror.py \
      --source "https://github.com/szilard-nemeth/yarn-dev-tools.git" \
      --mirror "https://github.infra.cloudera.com/snemeth/yarn-dev-tools-mirror.git" \
      --source-branch "${1:-"master"}" \
      --target-branch "${2:-"master"}" \
      --force

  echo "Exit code of $HOME_LINUXENV_DIR/scripts/git/git_repo_mirror.py: $?"
}

function sync-linux-env-repo {
    echo "Initiating sync for branch: $SYNC_BRANCH"

    # Invoke the Python script
    # --force is added here to make it non-interactive
    python3 "$HOME_LINUXENV_DIR"/scripts/git/git_repo_mirror.py \
        --source "git@github.com:szilard-nemeth/linux-env.git" \
        --mirror "git@github.infra.cloudera.com:snemeth/linux-env-mirror.git" \
        --source-branch "${1:-"master"}" \
        --target-branch "${2:-"master"}" \
        --force

    echo "Exit code of $HOME_LINUXENV_DIR/scripts/git/git_repo_mirror.py: $?"
}

function sync-kb-private-repo {
    python3 "$HOME_LINUXENV_DIR"/scripts/git/git_repo_mirror.py \
        --source "git@github.com:szilard-nemeth/knowledge-base-private.git" \
        --mirror "git@github.infra.cloudera.com:snemeth/knowledge-base-mirror.git" \
        --source-branch "${1:-"master"}" \
        --target-branch "${2:-"master"}" \
        --force
}

function sync-kb-private-repo-filter-dir {
    python3 "$HOME_LINUXENV_DIR"/scripts/git/git_repo_mirror.py \
        --source "git@github.com:szilard-nemeth/knowledge-base-private.git" \
        --mirror "git@github.infra.cloudera.com:snemeth/knowledge-base-mirror.git" \
        --source-branch "${1:-"master"}" \
        --target-branch "${2:-"master"}" \
        --filter-dir "cloudera" \
        --force
}

function sync-spark-experiments-repo {
    python3 "$HOME_LINUXENV_DIR"/scripts/git/git_repo_mirror.py \
        --source "git@github.com:szilard-nemeth/spark-experiments.git" \
        --mirror "git@github.infra.cloudera.com:snemeth/spark-experiments.git" \
        --source-branch "${1:-"master"}" \
        --target-branch "${2:-"master"}" \
        --force
}