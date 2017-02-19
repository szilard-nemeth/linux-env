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


declare -a COPY_LIST=()
COPY_LIST+=("$DIR/aliases/. $HOME/aliases/")
COPY_LIST+=("$DIR/dotfiles/. $HOME/")
COPY_LIST+=("$DIR/scripts/. $HOME/scripts")
COPY_LIST+=("$DIR/.bashrc $HOME/.bashrc")
COPY_LIST+=("$DIR/dotfiles/i3/. $HOME/.i3/")
COPY_LIST+=("$DIR/workplace-specific/. $HOME/workplace-specific")

copy_entries "${COPY_LIST[@]}"

echo Sourcing files from $HOME/aliases;
for f in $HOME/aliases/*.sh; do
  echo Sourcing file $f
  . "$f"
done
echo Done sourcing files from ~/aliases;

echo "Searching for .add-to-path files and adding them to PATH..."
matched_dirs=$(find $HOME/workplace-specific/ -name .add-to-path -printf "%h\n")
for d in $matched_dirs; do
  echo "Adding files from directory $d to PATH..."
  PATH=$PATH:$d
done

echo "Searching for .source-this files and sourcing them..."
matched_dirs=$(find $HOME/workplace-specific/ -name .source-this -printf "%h\n")
for d in $matched_dirs; do
  echo "Sourcing files from $d"
  for f in $(find $d -maxdepth 1 -iname  "*.sh"); do
    echo "Sourcing file $f"
    . "$f"
  done
done
