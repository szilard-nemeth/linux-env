#!/usr/bin/env bash

find_file() {
  files=("${(@f)$(find . -type f -name "$1")}")
  
  # Handle edge case: empty result produces one empty string in array
  if [[ -z "$files[1]" ]]; then
    echo "Error: No $1 file found in repo." >&2
    return 1
  fi

  if (( ${#files[@]} > 1 )); then
    echo "Error: Multiple $1 files found:" >&2
    for f in "${files[@]}"; do
      echo "  $f" >&2
    done
    return 1
  fi

  echo "${files[1]}"  # zsh arrays are 1-indexed
}