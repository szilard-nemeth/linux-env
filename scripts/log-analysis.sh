#!/usr/bin/env bash

function loganalysis-strip-date {
  src_file=$1
  dst_file=$2
  cut -d" " -f3-200 "$src_file" | sort | uniq > "$dst_file"
}

function loganalysis-split-file {
  from=$1
  to=$2
  src_file=$3
  dst_file=$4
  sed -n "$from,$to"p $src_file > $dst_file
}