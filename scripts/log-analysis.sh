#!/usr/bin/env bash

function loganalysis-strip-date {
  src_file=$1
  dst_file=$2
  cut -d" " -f3-200 "$src_file" | sort | uniq > "$dst_file"
}

function loganalysis-split-file {
  if [ $# -ne 3 ]; then
    echo "Usage: $0 <from line> <to line> <file>"
    return 1
  fi

  from=$1
  to=$2
  src_file=$3
  sed -n "$from,$to"p $src_file
}

function loganalysis-head-tail {
  stdin=$(</dev/stdin)
  echo $stdin | head -n 15
  echo "..."
  echo "..."
  echo $stdin | tail -n 15
}

function loganalysis-get-linenumber-for-pattern {
  src_file="$1"
  pattern="$2"
  grep -n $pattern $src_file | grep -Eo '^[^:]+'
}