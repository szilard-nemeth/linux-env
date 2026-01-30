#!/bin/bash

# This script lists all Git branches with their latest commit date,
# sorted from newest to oldest.

# Ensure we are in a Git repository
if [ ! -d .git ]; then
  echo "Error: Not a Git repository."
  exit 1
fi

# List all local branches, and for each one, get the commit date of the
# latest commit. The output is then sorted by the date.
git for-each-ref --sort='-committerdate' --format='%(committerdate:short) %(refname:short)' refs/heads refs/remotes