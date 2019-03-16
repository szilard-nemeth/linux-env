
1. Function to check status of command: 
```
function check_status_of_cmd {
    "$@"
    local status=$?
    if [ $status -ne 0 ]; then
        echo "error with $1" >&2
    fi
    return $status
}
```