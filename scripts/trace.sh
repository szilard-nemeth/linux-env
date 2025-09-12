function debug-command {
    local cmd=$1
    local grep_for=$2
    set -x;
    ${cmd} 2>&1; 
    set +x;
}

start_trace_logging() {
    # USAGE EXAMPLE: 
    # local logfile=$(start_trace_logging)
    # echo "Tracing to file: $logfile"
    # trace_to_file $logfile echo "test1"
    # trace_to_file $logfile echo "test2"
    
    local caller="${FUNCNAME[1]:-main}"
    local timestamp="$(date +%Y%m%d_%H%M%S%N)"
    local logfile="/tmp/trace_${caller}_${timestamp}.log"
    echo "$logfile"
}

get_latest_trace_log() {
    # USAGE EXAMPLE: 
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
        echo "Usage: trace_to_file logfile command [args...]" >&2
        return 1
    fi

    # Naive approach, prints:
    # +trace_to_file:19> echo faf
    # +trace_to_file:20> set +x
    # {
    #     set -x
    #     "$@"
    #     set +x
    # } 2>&3

    local logfile=$1
    shift

    local cmd_str=""
    for arg in "$@"; do
        cmd_str+=" $(printf '%q' "$arg")"
    done

    #1. Saving original stderr (FD 2) to another descriptor (say, FD 4).
    #2. Creating a new FD (e.g., FD 3) for tracing.
    #3. Redirecting only xtrace to FD 3.
    #4. Letting FD 2 (normal stderr) continue to the shell.
    exec 3>>"$logfile" 4>&2
    {
        PS4=$'%D{%Y-%m-%d %H:%M:%S} + '
        setopt prompt_subst
        set -x
        eval "$cmd_str"
        set +x
    } 2>&3  # Only trace output goes here

    # Restore stderr
    exec 3>&- 4>&-
}

###########
function demo_trace_to_file {
    local logfile=$(start_trace_logging)
    echo "Tracing to file: $logfile"
    trace_to_file "$logfile" echo "faf"
    trace_to_file "$logfile" echo "faf2"
}