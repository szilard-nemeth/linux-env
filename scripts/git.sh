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