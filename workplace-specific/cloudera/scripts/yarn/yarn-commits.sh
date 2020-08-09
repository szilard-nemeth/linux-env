#!/usr/bin/env bash

GIT_LOG_PY_SCRIPT="git_log_cmd_generator.py"
MY_NAME_VARIATIONS="snemeth Szilard 'Szilard Nemeth'"
MY_APACHE_MAIL="'snemeth@apache.org'"
MY_APACHE_USERNAME="snemeth"
PROJECTS="'YARN\|SUBMARINE\|HADOOP'"

function hadoop-upstream-stats-projects() {
    get-hadoop-upstream-stats "$GIT_LOG_PY_SCRIPT --grep $MY_NAME_VARIATIONS --oneline --final-grep $PROJECTS"
}

function hadoop-upstream-stats-count-projects() {
    get-hadoop-upstream-stats "$GIT_LOG_PY_SCRIPT --grep $MY_NAME_VARIATIONS --oneline --count --final-grep $PROJECTS"
}

function hadoop-upstream-stats-count() {
    get-hadoop-upstream-stats "$GIT_LOG_PY_SCRIPT --grep $MY_NAME_VARIATIONS --oneline --count"
}

function hadoop-upstream-stats-committed() {
    get-hadoop-upstream-stats "$GIT_LOG_PY_SCRIPT --author $MY_APACHE_MAIL --oneline --count"
}

function hadoop-upstream-stats-all() {
    commits=$(get-hadoop-upstream-stats "$GIT_LOG_PY_SCRIPT --grep $MY_NAME_VARIATIONS --oneline --count --trim-count")
    committed=$(get-hadoop-upstream-stats "$GIT_LOG_PY_SCRIPT --author $MY_APACHE_USERNAME --oneline --count --trim-count")
    num_commits=$(echo ${commits} | tail -n1)
    num_committed=$(echo ${committed} | tail -n1)
    total=$(expr "$num_commits" + "$num_committed")
    echo "All commits: $num_commits"
    echo "All committed: $num_committed"
    echo "Grand total: $total"
}

function hadoop-upstream-stats-count-by-person() {
    NAME_VARIATIONS="$1"
    get-hadoop-upstream-stats "$GIT_LOG_PY_SCRIPT --grep $NAME_VARIATIONS --oneline --count"
}

function hadoop-upstream-stats-by-person() {
    NAME_VARIATIONS="$1"
    get-hadoop-upstream-stats "$GIT_LOG_PY_SCRIPT --grep $NAME_VARIATIONS --oneline"
}

function get-hadoop-upstream-stats() {
#    set -x
    local cmd=$1
    goto-hadoop;
    result=$(eval ${cmd})
    echo "Running command: $result"
    eval ${result}
    cd - 2>&1 1>/dev/null
#    set +x
}
