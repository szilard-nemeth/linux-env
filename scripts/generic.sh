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

start_trace_logging() {
    local caller="${FUNCNAME[1]:-main}"
    local timestamp="$(date +%Y%m%d_%H%M%S%N)"
    local logfile="/tmp/trace_${caller}_${timestamp}.log"
    echo "Logging trace to $logfile"
}

get_latest_trace_log() {
    # Should be used like: 
    # local logfile=$(start_trace_logging)
    # echo "Tracing to file: $logfile"
    # OR
    # echo "Latest trace log:"
    # local latest_log=$(get_latest_trace_log)
    # echo "$latest_log"
    # cat "$latest_log"


    local caller="${FUNCNAME[1]:-main}"
    local latest_file=$(ls -t /tmp/trace_${caller}_*.log(N) 2>/dev/null | head -n1)

    if [[ -n $latest_file ]]; then
        echo "$latest_file"
    else
        echo "No trace files found for caller '$caller'." >&2
        return 1
    fi
}


trace_to_file() {
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

    local cmd_str=""
    for arg in "$@"; do
        cmd_str+=" $(printf '%q' "$arg")"
    done

    # Naive approach, prints:
    #   +trace_to_file:19> echo faf
    #   +trace_to_file:20> set +x
    #   {
    #       set -x
    #       "$@"
    #       set +x
    #   } 2>&3

    {
        PS4=$'%D{%Y-%m-%d %H:%M:%S} + '
        setopt prompt_subst
        set -x
        eval "$cmd_str"
        set +x
    } 2>>"$logfile"    # Redirect only stderr (trace output) and append 
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