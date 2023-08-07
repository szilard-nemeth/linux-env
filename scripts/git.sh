#!/bin/bash

function commit-all-unstaged() {
    for i in $(git diff --name-only); do
        git add ${i}
    done
    git commit
}

function git-search-branches() {
    for sha1 in `git log --oneline --all --grep "$1" | cut -d" " -f1`
    do
        git branch -r --contains ${sha1}
    done
}
function git-search-tags() {
    for sha1 in `git log --oneline --all --grep "$1" | cut -d" " -f1`
    do
        git tag --contains ${sha1}
    done
}

function git-precommit() {
  .git/hooks/pre-commit
}

function gitconfig-private() {
    git config user.email "szilard.nemeth88@gmail.com"
    git config user.name "Szilard Nemeth"
}

function gitconfig-cloudera() {
    git config user.email snemeth@cloudera.com
    git config user.name "Szilard Nemeth"
}

function gh-apply-patch() {
  if [ $# -ne 1 ]; then
    echo "Usage: gh-apply-patch <pr_id>" 1>&2
    return 1
  fi

  PR_ID=$1
  gh pr diff $PR_ID > /tmp/github-pr-$PR_ID.patch
  git apply /tmp/github-pr-$PR_ID.patch
}

# TODO Move all cde aliases to a separate git.sh script
function git-sync-cde-develop {
    set -x
    orig_branch=$(git rev-parse --abbrev-ref HEAD)
    git fetch origin
    git checkout develop
    git rebase origin/develop
    git status
    git checkout $orig_branch
    set +x
}

function git-sync-cde-featurebranch {
    set -x
    orig_branch=$(git rev-parse --abbrev-ref HEAD)
    git fetch origin
    git checkout develop
    git rebase origin/develop
    git status
    git checkout $orig_branch
    git rebase develop
    git --no-pager log -1 --oneline
    set +x
}

function git-format-patch {
    #alias git-save-all-commits="git format-patch $(git rev-list --max-parents=0 HEAD)..HEAD -o /tmp/patches"
    if [ $# -ne 2 ]; then
        echo "Usage: git-format-patch <base branch> <destination dir>" 1>&2
        return 1
    fi
    local base_branch=$1
    local dest_dir=$2

    git format-patch $base_branch..HEAD -o $dest_dir
}

function git-backup-patch-develop-formatpatch {
    #cd $DEX_DEV_ROOT
    local branch=$(git rev-parse --abbrev-ref HEAD)
    local output_dir="$CLOUDERA_TASKS_CDE_DIR/$branch/backup-patches/$(date-formatted)"
    echo "Output dir: $output_dir"
    mkdir -p $output_dir

    git-format-patch develop $output_dir
}

function git-backup-patch-develop-simple {
    set -x
    local branch=$(git rev-parse --abbrev-ref HEAD)
    local output_dir="$CLOUDERA_TASKS_CDE_DIR/$branch/backup-patches-single/"
    mkdir -p $output_dir
    local output_file="$output_dir/backup-$branch-$(date-formatted).patch"
    echo "Creating patch based on develop to: $output_file"
    git diff develop..HEAD > $output_file
    set +x
}

function git-squash-all-based-on-develop {
    # git checkout yourBranch
    COMMIT_MSG="$(git branch --show-current) squashed"
    git reset $(git merge-base develop $(git branch --show-current))
    git add -A
    git commit -m "$COMMIT_MSG"
}



