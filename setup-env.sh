#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

mkdir -p $HOME/.env
ENV_FILE_MAPPINGS=$HOME/.env/.file-mappings
rm ${ENV_FILE_MAPPINGS}
touch ${ENV_FILE_MAPPINGS}

HOME_LINUXENV_DIR="$HOME/.linuxenv/"
WORKPLACE_SPECIFIC_DIR="$HOME_LINUXENV_DIR/workplace-specific/"

function copy_files() {
    IFS=' ' read -ra copy_list <<< "$@"

    if [ $((${#copy_list[@]} % 2)) -ne 0 ]; then
        echo "Illegal number of parameters, should be even!"
        exit 1
    fi

    i="0"
    while [ ${i} -lt ${#copy_list[@]} ]; do
        from="${copy_list[$i]}"
        to="${copy_list[$i+1]}"

        if [[ -d "${from}" ]]; then
            mkdir -p ${to}
        elif [[ -f "${from}" ]]; then
            mkdir -p $(dirname ${to})
        fi

        if [[ "$from" == *. ]]; then
            echo "Copying files from $from to $to (recursive)"
            yes | cp -aR ${from} ${to}
            from_stripped=$(echo ${from} | sed 's/.$//')
            echo "$from_stripped $to" >> ${ENV_FILE_MAPPINGS}
        else
            echo "Copying file from $from to $to"
            cp ${from} ${to}
            echo "$from $to" >> ${ENV_FILE_MAPPINGS}
        fi

        i=$[$i+2]
    done
}

function source_scripts() {
    source_from=$1
    src_firs_orig="$2"
    src_first=${source_from}/${src_firs_orig}
    
    if [[ ! -z ${src_firs_orig}  ]]; then
        echo "Sourcing files first: $src_first"
        . "$src_first"
    fi
    
    echo Sourcing files from ${source_from};
    for f in ${source_from}/*.sh; do
        if [[ ! -z ${src_first} &&  "$f" = "$src_first" ]]; then
            echo "Skipping sourcing file again: $f"
            continue
        fi
        echo Sourcing file ${f}
        . "$f"
    done
    echo Done sourcing files from ${source_from};
}

function source_single_file() {
    src_file=$1
    echo "Sourcing file ${src_file}"
    . "$src_file"
}

function source_files() {
    local marker_file_name=$1
    local from_dir="$WORKPLACE_SPECIFIC_DIR"

    echo "Searching for $marker_file_name files and sourcing them..."
    set_matched_dirs ${WORKPLACE_SPECIFIC_DIR} ${marker_file_name}
    for d in ${matched_dirs}; do
        printf "\tSourcing files from $d\n"
        for f in $(find ${d} -maxdepth 1 -iname  "*.sh"); do
            printf "\tSourcing file $f\n"
            . "$f"
        done
    done
    echo "Done sourcing $marker_file_name files from $from_dir"
}

function add_to_path() {
    marker_file_name=$1
    from_dir="$WORKPLACE_SPECIFIC_DIR"

    echo "Searching for $marker_file_name files and adding them to PATH..."
    set_matched_dirs ${from_dir} ${marker_file_name}
    for d in ${matched_dirs}; do
        printf "\tAdding files from directory $d to PATH...\n"
        PATH=$PATH:${d}
    done
    echo "Done sourcing $marker_file_name files from $from_dir"
}

function set_matched_dirs() {
    local from_dir=$1
    local marker_file_name=$2

    #matched_dirs will contain full path of the directory containing marker_file_name
    #https://stackoverflow.com/a/2282701/1106893
    ##compatible with GNU find:
    ## matched_dirs=$(find $from_dir -name $marker_file_name -printf "%h\n")

    #compatible with MacOS / FreeBSD
    matched_dirs=$(find ${from_dir} -name ${marker_file_name} -print0 | xargs -0 -n1 dirname | sort --unique)
}

function initial_setup_macos() {
    echo "Running initial macOS setup"
    echo "Checking whether Homebrew is installed..."
    if ! hash brew 2>/dev/null; then
        echo "Homebrew not found! Installing Homebrew..."
        /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    fi
    
    echo "Checking whether GNU sed is available..."
    echo "123 abc" | sed -r 's/[0-9]+/& &/' > /dev/null
    if [[ "$?" -ne 0 ]]; then
        echo "Installing GNU sed"
        brew install gnu-sed --with-default-names
    fi
    
    echo "Checking whether npm is available..."
    if ! hash node 2>/dev/null; then
        brew install node;
        which node # => /usr/local/bin/node
        mkdir "${HOME}/.npm-packages"
    fi
    npm list -g figlet-cli 1>2 2>/dev/null && echo "Figlet is already installed" || { echo "Installing figlet";npm install -g figlet-cli; }
    
    #gettext is required because it contains envsubst
    brew list gettext 1>2 2>/dev/null
    if [ "$?" -ne 0 ]; then
        echo "Installing gettext"
        brew install gettext
        brew link --force gettext
    else
        echo "gettext is already installed"
    fi
    echo "complete" > "${HOME}/.env/.initial-setup-status"
}

function determine_platform() {
    platform='unknown'
    unamestr=`uname`
    if [[ "$unamestr" == 'Linux' ]]; then
       platform='linux'
    elif [[ "$unamestr" == 'FreeBSD' ]]; then
       platform='freebsd'
    elif [[ "$unamestr" == 'Darwin' ]]; then
       platform='macOS'
    fi
    echo ${platform}
}

function copy_files_from_linuxenv_repo_to_home() {
    declare -a COPY_LIST=()
    COPY_LIST+=("$DIR/.bashrc $HOME/.bashrc")
    COPY_LIST+=("$DIR/.bash_profile $HOME/.bash_profile")
    COPY_LIST+=("$DIR/setup-vars.sh $HOME_LINUXENV_DIR/setup-vars.sh")
    COPY_LIST+=("$DIR/dotfiles/. $HOME/")
    COPY_LIST+=("$DIR/aliases/. $HOME_LINUXENV_DIR/aliases/")
    COPY_LIST+=("$DIR/scripts/. $HOME_LINUXENV_DIR/scripts")
    COPY_LIST+=("$DIR/workplace-specific/. $WORKPLACE_SPECIFIC_DIR")
    COPY_LIST+=("$DIR/.npmrc $HOME/.npmrc")
    
    #Can't use is-platform-macos alias here as it's not yet loaded
    if [[ ! ${platform} == 'macOS' ]]; then
        COPY_LIST+=("$DIR/dotfiles/i3/. $HOME/.i3/")
    else
        echo "$INFO_PREFIX Skip copying i3 files as platform is $platform"
    fi
    
    set -e
    copy_files "${COPY_LIST[@]}"
    set +e
    
    # !!! THE ORDER OF THE FOLLOWING SOURCE COMMANDS ARE STRICT !!!
    #source and add to path happens from $WORKPLACE_SPECIFIC_DIR/**
    source_single_file "${HOME_LINUXENV_DIR}/scripts/load-these-first.sh"
    source_single_file "${HOME_LINUXENV_DIR}/setup-vars.sh"
    source_scripts ${HOME_LINUXENV_DIR}/aliases
    source_scripts ${HOME_LINUXENV_DIR}/scripts
    source_files ".source-this"
    add_to_path ".add-to-path"
}

platform=$(determine_platform)
echo "Platform is: $platform"
if [[ ${platform} == 'macOS' ]] && ! grep -q "complete" "$HOME/.env/.initial-setup-status"; then
    initial_setup_macos
fi

INFO_PREFIX="--->"
copy_files_from_linuxenv_repo_to_home
