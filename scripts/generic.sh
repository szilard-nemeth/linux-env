#!/usr/bin/env bash

function svim {
    sudo vim -u /home/${USER}/.vimrc $1
}

function debug-command {
    local cmd=$1
    local grep_for=$2
    set -x;
    ${cmd} 2>&1; 
    set +x;
}

function trace_to_file {
    if (( $# < 2 )); then
        echo "Usage: trace_to_file logfile command [args...]"
        echo "Usage: trace_to_file mytrace.log bash -c '
            echo "Running multiple commands"
            ls -l /nonexistent
        '"  
    return 1
    fi

    local logfile=$1
    shift


    # Open FD 3 for writing to the logfile
    exec 3>"$logfile"

    # Naive approach, prints: 
    # +trace_to_file:19> echo faf
    # +trace_to_file:20> set +x
    # {
    #     set -x
    #     "$@"
    #     set +x
    # } 2>&3


    # Quote and join arguments safely
    local cmd_str=""
    for arg in "$@"; do
        cmd_str+=" $(printf '%q' "$arg")"
    done

    # Set PS4 to include a timestamp
    local ps4='+$(date "+%Y-%m-%d %H:%M:%S") '
    {
        PS4="$ps4"
        set -x
        eval "$cmd_str"
        set +x
    } 2>&3

    # Close FD 3
    exec 3>&-
}


function show-funcdef {
  declare -f $1
}

function grep-text {
    if [ $# -ne 1 ]; then
        echo "Usage: grep-text <pattern>" 1>&2
        return 1
    fi

    grep $1 . -lRI --exclude=\*{log,json,html,mhtml}
}

function grep-text-regrep {
    if [ $# -ne 1 ]; then
        echo "Usage: grep-text <pattern>" 1>&2
        return 1
    fi

    results=$(grep $1 . -lRI --exclude=\*{log,json,html,mhtml})
    # 1. Print results
    echo "RESULTS: " 
    echo $results

    echo "GREPPING PATTERN AGAIN IN RESULTED FILES: "
    # 2. Grep pattern again in resulted files
    # Truncate long matching lines: https://stackoverflow.com/a/63165087
    echo $results | xargs grep -oE ".{0,10}$1.{0,10}"
}

function grep-text-files {
    grep -inr --include \*.md --include \*.txt $1 $2
}