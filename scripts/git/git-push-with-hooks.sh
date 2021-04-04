#!/bin/bash
#CREDITS TO: https://stackoverflow.com/a/3812238/1106893

set -x
GIT_DIR_="$(git rev-parse --git-dir)"
BRANCH="$(git rev-parse --symbolic --abbrev-ref $(git symbolic-ref HEAD))"

PRE_PUSH="$GIT_DIR_/hooks/pre-push"
POST_PUSH="$GIT_DIR_/hooks/post-push"

test -x "$PRE_PUSH" && echo "Executing $PRE_PUSH" exec "$PRE_PUSH" "$BRANCH" "$@"
git push "$@"
test $? -eq 0 && test -x "$POST_PUSH" && echo "Executing $POST_PUSH" && exec "$POST_PUSH" "$BRANCH" "$@"
set +x