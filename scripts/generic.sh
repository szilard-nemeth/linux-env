#!/usr/bin/env bash

function svim {
    sudo vim -u /home/${USER}/.vimrc $1
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

function grep-shell-scripts {
    grep -inr --include \*sh --include \*.zsh $1
}

function grep-text-md-files {
    grep -inr --include \*txt --include \*.md $1
}

function grep-text-md-files-filenames {
    set -x
    grep -linr --include \*txt --include \*.md "$1" | sort | uniq
}

