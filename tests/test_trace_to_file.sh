#!/usr/bin/env zsh
# Simple manual test for trace_to_file function in zsh

# Source your script with the function
# set -e  # Optional: stop on any unhandled error
# set -u  # Optional: error on unset variables

source "$(dirname "${(%):-%x}")/./common.sh"

target_file=$(find_file trace.sh) || {
  echo "Failed to find trace2.sh. Exiting." >&2
  exit 1
}
source $target_file


tmpfile=$(mktemp /tmp/trace_test_XXXXXX)
logfile="${tmpfile}.log"
mv "$tmpfile" "$logfile" || {
  echo "Failed to rename temp file" >&2
  exit 1
}

echo "Running trace_to_file with a command producing stdout and stderr..."

# Capture stdout of the command; stderr redirected to stdout here
output=$(trace_to_file "$logfile" zsh -c 'echo "stdout"; echo "stderr" >&2; ls /nonexistent' 2>&1)
local result=$?

echo "Command exit status: $result"
echo "Command stdout+stderr captured:"
print -r -- "$output"

echo "Contents of trace log ($logfile):"
cat "$logfile"

# Simple checks
if grep -q '^echo "stdout"' "$logfile"; then
  echo "Trace log should not contain the command trace."
  exit 1
else
  echo "Trace log missing command trace, this is correct!"
fi


rm "$logfile"
echo "Test passed."
