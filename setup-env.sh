#!/usr/bin/env bash


###############################
function initial_setup() {
    if test -n "$ZSH_VERSION"; then
        PROFILE_SHELL=zsh
    elif test -n "$BASH_VERSION"; then
        PROFILE_SHELL=bash
    elif test -n "$KSH_VERSION"; then
        PROFILE_SHELL=ksh
    elif test -n "$FCEDIT"; then
        PROFILE_SHELL=ksh
    elif test -n "$PS3"; then
        PROFILE_SHELL=unknown
    else
        PROFILE_SHELL=sh
    fi
    
    if [[ "$PROFILE_SHELL" == 'zsh' ]]; then
       DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    elif [[ "$PROFILE_SHELL" == 'bash' ]]; then
       DIR="$LINUX_ENV_REPO"
    fi
    
    #Declare common variables
    HOME_ENV="$HOME/.env/"
    ENV_SETUP_STATUS="$HOME_ENV/.initial-setup-status"
    
    HOME_LINUXENV_DIR="$HOME/.linuxenv/"
    WORKPLACE_SPECIFIC_DIR="$HOME_LINUXENV_DIR/workplace-specific/"
    INFO_PREFIX="--->"
    
    #Invoke common functions
    platform=$(determine_platform)
    echo "Platform is: $platform"
    
    #Initial setup platforms: Only macOS is implemented
    if [[ ${platform} == 'macOS' ]] && ! grep -q "complete" "$ENV_SETUP_STATUS"; then
        initial_setup_macos
    fi
}

function copy_files() {
    #echo "Arguments to copy files: $@"
    
    #Init env file mappings
    mkdir -p $HOME/.env
    ENV_FILE_MAPPINGS=${HOME_ENV}/.file-mappings
    rm ${ENV_FILE_MAPPINGS}
    touch ${ENV_FILE_MAPPINGS}

    
    if [[ "$PROFILE_SHELL" == 'zsh' ]]; then
       IFS=' ' read -rA copy_list <<< "$@"
       #Arrays are initialized from 1 in ZSH
       i="1"
    elif [[ "$PROFILE_SHELL" == 'bash' ]]; then
       IFS=' ' read -ra copy_list <<< "$@"
       i="0"
    fi
    unset IFS
    
    if [ $((${#copy_list[@]} % 2)) -ne 0 ]; then
        echo "Illegal number of parameters, should be even!"
        exit 1
    fi

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
    src_first_orig="$2"
    src_first=${source_from}/${src_first_orig}
    
    if [[ ! -z ${src_first_orig}  ]]; then
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
    
    #Source each *.sh file from matched dirs
    #Priority: setup.sh files
    for d in ${matched_dirs}; do
        setup_sh="$d/setup.sh"
        if [[ -f "$setup_sh" ]]; then
            printf "\tSourcing setup file $setup_sh\n"
            . "$setup_sh"
        fi
    done
    
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
    matched_dirs=($(find ${from_dir} -name ${marker_file_name} -print0 | xargs -0 -n1 dirname | sort --unique))
}

#TODO migrate all programs to use this function
function brew_install() {
    local program=$1
    
    brew ls --versions ${program}
    if [[ "$?" -ne 0 ]]; then
        echo "Installing $program with brew ..."
        brew install ${program}
    else
        echo "Note: $program is already installed with brew."
    fi
}

#TODO migrate all programs to use this function
#TODO Optimize: brew search --casks is pretty slow: Could query multiple programs to speed up: brew search --casks prog1 prog2 progn
#https://discourse.brew.sh/t/how-can-i-get-a-list-of-the-available-casks/6769
function brew_cask_install() {
    local program=$1
    
    brew search --casks ${program}
    if [[ "$?" -ne 0 ]]; then
        echo "Installing $program with brew cask..."
        brew cask install ${program}
    else
        echo "Note: $program is already installed with brew cask."
    fi
}


function initial_setup_macos() {
    echo "=== Running initial macOS setup ==="
    echo "Checking whether Homebrew is installed..."
    if ! hash brew 2>/dev/null; then
        echo "Homebrew not found! Installing Homebrew..."
        /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    fi
    
    echo "Checking whether GNU sed is installed..."
    echo "123 abc" | sed -r 's/[0-9]+/& &/' > /dev/null
    if [[ "$?" -ne 0 ]]; then
        echo "Installing GNU sed"
        brew install gnu-sed --with-default-names
    fi
    
    echo "Checking whether npm is installed..."
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
    
    echo "Checking available shells..."
    cat /etc/shells | grep zsh
    if [[ "$?" -ne 0 ]]; then
        echo "Installing zsh"
        brew install zsh
    fi
    
    echo "Checking whether antigen is installed..."
    if ! hash antigen 2>/dev/null; then
        echo "Installing antigen"
        brew install antigen
    fi
    
    echo "Checking whether kitty is installed..."
    if ! hash kitty 2>/dev/null; then
        echo "Installing kitty"
        brew cask install kitty
    fi
    
    echo "Installing fonts..."
    brew_cask_install font-mononoki-nerd-font
    brew_cask_install font-hack-nerd-font
    brew_cask_install font-monoid-nerd-font
    
    echo "complete" > "${ENV_SETUP_STATUS}"
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
    
    #Bash
    COPY_LIST+=("$DIR/.bashrc $HOME/.bashrc")
    COPY_LIST+=("$DIR/.bash_profile $HOME/.bash_profile")
    
    #zsh
    COPY_LIST+=("$DIR/.zshrc $HOME/.zshrc")
    COPY_LIST+=("$DIR/.zprofile $HOME/.zprofile")
    
    COPY_LIST+=("$DIR/setup-vars.sh $HOME_LINUXENV_DIR/setup-vars.sh")
    COPY_LIST+=("$DIR/dotfiles/. $HOME/")
    COPY_LIST+=("$DIR/aliases/. $HOME_LINUXENV_DIR/aliases/")
    COPY_LIST+=("$DIR/scripts/. $HOME_LINUXENV_DIR/scripts")
    COPY_LIST+=("$DIR/workplace-specific/. $WORKPLACE_SPECIFIC_DIR")
    COPY_LIST+=("$DIR/.npmrc $HOME/.npmrc")
    
    #Kitty conf + theme
    COPY_LIST+=("$DIR/config/kitty.conf $HOME/.config/kitty/kitty.conf")
    COPY_LIST+=("$DIR/config/theme.conf $HOME/.config/kitty/theme.conf")
    
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


#####################################
initial_setup
copy_files_from_linuxenv_repo_to_home
set +x