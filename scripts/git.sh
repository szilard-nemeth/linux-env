#!/bin/bash

function commit-all-unstaged() {
    for i in $(git diff --name-only); do
        git add ${i}
    done
    git commit
}