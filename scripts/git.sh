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

function gh-apply-patch {
  if [ $# -ne 1 ]; then
    echo "Usage: gh-apply-patch <pr_id>" 1>&2
    return 1
  fi

  PR_ID=$1

  echo "Showing PR info..."
  gh pr view $PR_ID | head -n 20

  echo "Applying PR diff..."
  gh pr diff $PR_ID > /tmp/github-pr-$PR_ID.patch
  git apply /tmp/github-pr-$PR_ID.patch
}

function gh-diff-cde-backport {
  if [ $# -ne 2 ]; then
    echo "Usage: gh-apply-patch <pr id for develop> <pr id for feature branch>" 1>&2
    return 1
  fi
  # TODO: Port this to $OTHER_REPOS_DIR/gandras/hadoop-scripts (alias: yarn-backport-diff-generator-upstream)
  # Example usage: gh-diff-cde-backport 5421 5565
  # Example 
  # PR targeting develop: https://github.infra.cloudera.com/CDH/dex/pull/5421
  # PR targeting CDH:DEX-1.20: https://github.infra.cloudera.com/CDH/dex/pull/5565

  # TODO assert 2 jira ids are the same

  set -x
  PR_ID_MAIN_BR="$1"
  PR_ID_FEAT_BR="$2"

  echo "Showing PR info for main branch..."
  gh pr view $PR_ID_MAIN_BR | head -n 20

  echo "Showing PR info for feature branch..."
  gh pr view $PR_ID_FEAT_BR | head -n 20

  echo "Saving PR diff for develop..."
  gh pr diff $PR_ID_MAIN_BR > /tmp/github-pr-$PR_ID_MAIN_BR.patch

  echo "Saving PR diff for feature branch..."
  gh pr diff $PR_ID_FEAT_BR > /tmp/github-pr-$PR_ID_FEAT_BR.patch

  echo "Making diff of 2 PRs"

  diff /tmp/github-pr-$PR_ID_MAIN_BR.patch /tmp/github-pr-$PR_ID_FEAT_BR.patch > /tmp/github-pr-diff-$PR_ID_MAIN_BR_$PR_ID_FEAT_BR.diff
  set +x
}

function gh-checkout-pr {
    PR_ID="$1"
    BRANCHNAME="pr-review-$PR_ID"
    git fetch origin pull/$PR_ID/head:$BRANCHNAME
    git co $BRANCHNAME
}

function gh-backport-cde-pr {
    # Example: gh-backport-cde-pr 5669 DEX-1.20.1
    PR_ID=$1
    TARGET_R_BRANCH="$2"
    TARGET_L_BRANCH="pr-backport-$TARGET_R_BRANCH"
    FORK_BRANCH=fork
    FORK_REPO_NAME=snemeth

    #TODO Validate if target branch exists
    # TODO error if gh does not exist


    git fetch
    COMMIT_HASH=$(gh pr view $PR_ID --json mergeCommit | jq '.mergeCommit.oid' | tr -d "\"")
    PR_TITLE=$(gh pr view $PR_ID --json title  | jq '.title' | tr -d "\"")

    if git cat-file -t $COMMIT_HASH 2> /dev/null 
    then 
        echo "Found commit: $COMMIT_HASH"
        git --no-pager log  --format=%B -n 1 $COMMIT_HASH
    else 
        echo "Commit with hash $COMMIT_HASH not found"
        return 1
    fi

    git co -b $TARGET_L_BRANCH remotes/origin/$TARGET_R_BRANCH 
    git branch --unset-upstream # Untrack remote branch
    
    git cherry-pick -x $COMMIT_HASH

    if [[ "$?" -ne 0 ]]; then
        echo "Failed to cherry-pick commit: $COMMIT_HASH"
        return 2
    fi
    

    echo "Pushing..."
    #git push --dry-run
    #echo "Execute: "
    #echo "git push $TARGET_L_BRANCH -u fork $TARGET_R_BRANCH"
    set -x
    git push $TARGET_L_BRANCH -u $FORK_BRANCH $TARGET_R_BRANCH
    set +x


    echo "Creating backport PR..."
    gh pr create --draft --title $PR_TITLE --body "Backport of #$PR_ID" --base $TARGET_R_BRANCH --head $FORK_REPO_NAME:$TARGET_L_BRANCH 
    echo "NOTE: Remember to un-draft your PR"
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

    git-format-patch origin/develop $output_dir
}

function git-backup-patch-develop-simple {
    set -x
    local branch=$(git rev-parse --abbrev-ref HEAD)
    local output_dir="$CLOUDERA_TASKS_CDE_DIR/$branch/backup-patches-single/"
    mkdir -p $output_dir
    local output_file="$output_dir/backup-$branch-$(date-formatted).patch"
    echo "Creating patch based on develop to: $output_file"
    git diff origin/develop..HEAD > $output_file
    set +x
}

function git-squash-all-based-on-develop {
    # git checkout yourBranch
    COMMIT_MSG="$(git branch --show-current) squashed"
    git reset $(git merge-base develop $(git branch --show-current))
    git add -A
    git commit -m "$COMMIT_MSG"
}



