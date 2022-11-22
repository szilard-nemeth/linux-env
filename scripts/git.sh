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