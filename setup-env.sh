#!/usr/bin/env bash
#TODO add warning about overwrite before copying to home directory!

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

ENV_FILE_MAPPINGS=$HOME/.env/.file-mappings
mkdir -p $HOME/.env
rm $ENV_FILE_MAPPINGS
touch $ENV_FILE_MAPPINGS


function copy_entries() {
    #TODO parameter number check --> should be even, otherwise skip copy and error!
    #TODO check return value of cp before adding entry to $ENV_FILE_MAPPINGS

    IFS=' ' read -ra copy_list <<< "$@"

    if [ $((${#copy_list[@]} % 2)) -ne 0 ]; then
        echo "Illegal number of parameters, should be even!"
        exit 1
    fi

    i="0"
    while [ $i -lt ${#copy_list[@]} ]; do
        from="${copy_list[$i]}"
        to="${copy_list[$i+1]}"

        if [[ "$from" == *. ]]; then
            echo "Copying files from $from to $to (recursive)"
            yes | cp -aR $from $to
            echo "${from::-1} $to" >> $ENV_FILE_MAPPINGS
        else
            echo "Copying file from $from to $to"
            cp $from $to
            echo "$from $to" >> $ENV_FILE_MAPPINGS
        fi

        i=$[$i+2]
    done
}

function source_scripts() {
    source_from=$1

    echo Sourcing files from $HOME/aliases;
    for f in $source_from/*.sh; do
        echo Sourcing file $f
        . "$f"
    done
    echo Done sourcing files from $source_from;
}

function source_files() {
    marker_file_name=$1
    from_dir="$HOME/workplace-specific/"

    echo "Searching for $marker_file_name files and sourcing them..."
    matched_dirs=$(find $from_dir -name $marker_file_name -printf "%h\n")
    for d in $matched_dirs; do
        printf "\tSourcing files from $d\n"
        for f in $(find $d -maxdepth 1 -iname  "*.sh"); do
            printf "\tSourcing file $f\n"
            . "$f"
        done
    done
    echo "Done sourcing $marker_file_name files from $from_dir"
}

function add_to_path() {
    marker_file_name=$1
    from_dir="$HOME/workplace-specific/"

    echo "Searching for $marker_file_name files and adding them to PATH..."
    matched_dirs=$(find $from_dir -name $marker_file_name -printf "%h\n")
    for d in $matched_dirs; do
        printf "\tAdding files from directory $d to PATH...\n"
        PATH=$PATH:$d
    done
    echo "Done sourcing $marker_file_name files from $from_dir"
}


declare -a COPY_LIST=()
COPY_LIST+=("$DIR/aliases/. $HOME/aliases/")
COPY_LIST+=("$DIR/dotfiles/. $HOME/")
COPY_LIST+=("$DIR/scripts/. $HOME/scripts")
COPY_LIST+=("$DIR/.bashrc $HOME/.bashrc")
COPY_LIST+=("$DIR/dotfiles/i3/. $HOME/.i3/")
COPY_LIST+=("$DIR/workplace-specific/. $HOME/workplace-specific")

copy_entries "${COPY_LIST[@]}"
source_scripts $HOME/aliases
source_files ".source-this"
add_to_path ".add-to-path"