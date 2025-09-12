#!/usr/bin/env bash

function print_debug {
  if [[ $LINUXENV_DEBUG == 1 ]]; then
    echo $1
  fi
}

function printf_debug {
  if [[ $LINUXENV_DEBUG == 1 ]]; then
    printf "$1\n"
  fi
}

#TODO Make setup colored: error messages with red, standard messages with white, etc.
###############################
function initial_setup {
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
       DIR="$LINUX_ENV_REPO"
    elif [[ "$PROFILE_SHELL" == 'bash' ]]; then
       DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
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

function copy_files {
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
        return 1
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
          from_stripped=$(echo ${from} | sed 's/.$//')
          echo "$from_stripped $to" >> ${ENV_FILE_MAPPINGS}
          if diff -r "$from" "$to" 2>&1 > /dev/null ; then
            print_debug "No changes in files. SRC DIR: $from, DEST DIR: $to"
          else
            printf_debug "Copying files from $from to $to (recursive)"
            yes | cp -aR ${from} ${to}
          fi
        else
          print_debug "$from $to" >> ${ENV_FILE_MAPPINGS}
          if cmp -s "$from" "$to" ; then
            print_debug "No changes in file. SRC: $from, DEST: $to"
          else
            print_debug "Copying file from $from to $to"
            cp ${from} ${to}
          fi
        fi
        i=$[$i+2]
    done
}

function source_scripts {
    source_from=$1
    src_first_orig="$2"
    src_first=${source_from}/${src_first_orig}
    
    if [[ ! -z ${src_first_orig}  ]]; then
        printf_debug "Sourcing files first: $src_first"
        . "$src_first"
    fi
    
    printf_debug "Sourcing files from ${source_from}"
    for f in ${source_from}/*.sh; do
        if [[ ! -z ${src_first} &&  "$f" = "$src_first" ]]; then
            printf_debug "Skipping sourcing file again: $f"
            continue
        fi
        # Uncomment this if file exclude is required
#        if [[ $f == *"upgrade-python-packages.sh"* ]]; then
#          printf_debug "Skip sourcing file: $f"
#        else
#          printf_debug "Sourcing file ${f}"
#          . "$f"
#        fi
        printf_debug "Sourcing file ${f}"
        . "$f"
    done
    printf_debug "Done sourcing files from ${source_from}"
}

function source_single_file {
    src_file=$1
    printf_debug "Sourcing file ${src_file}"
    . "$src_file"
}

function source_files {
    local marker_file_name=$1
    local from_dir="$WORKPLACE_SPECIFIC_DIR"

    printf_debug "Searching for $marker_file_name files and sourcing them..."
    set_matched_dirs ${WORKPLACE_SPECIFIC_DIR} ${marker_file_name}
    
    #Source each *.sh file from matched dirs
    #Priority: setup.sh files
    for d in ${matched_dirs}; do
        setup_sh="$d/setup.sh"
        if [[ -f "$setup_sh" ]]; then
            printf_debug "\tSourcing setup file $setup_sh\n"
            . "$setup_sh"
        fi
    done

    for d in ${matched_dirs}; do
        printf_debug "\tSourcing files from $d"
        for f in $(find ${d} -maxdepth 1 -iname  "*.sh" -not -iname "setup.sh" | xargs grep -L "##SKIPSOURCING##"); do
            printf_debug "\tSourcing file $f"
            . "$f"
        done
    done
    printf_debug "Done sourcing $marker_file_name files from $from_dir"
}

function add_to_path {
    marker_file_name=$1
    from_dir="$2"

    printf_debug "Searching for $marker_file_name files and adding them to PATH..."
    set_matched_dirs ${from_dir} ${marker_file_name}
    for d in ${matched_dirs}; do
        printf_debug "\tAdding files from directory $d to PATH...\n"
        PATH=$PATH:${d}
    done
    printf_debug "Done sourcing $marker_file_name files from $from_dir"
}

function add_to_path_directly {
    dir=$1
    printf_debug "Adding directory: $dir to PATH"
    PATH=$PATH:${dir}
}

function set_matched_dirs {
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
function brew_install {
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
function brew_cask_install {
    local program=$1
    
    brew search --casks ${program}
    if [[ "$?" -ne 0 ]]; then
        echo "Installing $program with brew cask..."
        brew install --cask ${program}
    else
        echo "Note: $program is already installed with brew cask."
    fi
}

function check_version {
    local program="$1"
    local currentver=$(eval $2)
    local requiredver="$3"
    
    if [ "$(printf '%s\n' "$requiredver" "$currentver" | sort -V | head -n1)" = "$requiredver" ]; then 
        echo "$program has version >= $requiredver"
        VERSIONCHECK_RESULT=0
    else
        echo "$program has version < $requiredver"
        VERSIONCHECK_RESULT=1
    fi
}

function initial_setup_macos {
    echo "=== Running initial macOS setup ==="
    echo "Checking if Homebrew is installed..."
    if ! hash brew 2>/dev/null; then
        echo "Homebrew not found! Installing Homebrew..."
        # Warning: The Ruby Homebrew installer is now deprecated and has been rewritten in
        # Bash. Please migrate to the following command:
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
    fi
    
    echo "Checking if GNU sed is installed..."
    echo "123 abc" | sed -r 's/[0-9]+/& &/' > /dev/null
    if [[ "$?" -ne 0 ]]; then
        echo "Installing GNU sed"
        brew install gnu-sed --with-default-names
    fi
    
    echo "Checking if npm is installed..."
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

    if ! hash tig 2>/dev/null; then
        echo "tig not found! Installing tig..."
        brew install tig
    fi

    if ! hash safe-rm 2>/dev/null; then
        echo "safe-rm not found! Installing safe-rm..."
        brew install safe-rm
    fi

    if ! hash wget 2>/dev/null; then
        echo "wget not found! Installing wget..."
        brew install wget
    fi

    echo "Checking if thefuck is installed..."
    if ! hash fuck 2>/dev/null; then
        echo "Installing thefuck"
        brew install thefuck
    fi

    echo "Checking available shells..."
    cat /etc/shells | grep zsh
    if [[ "$?" -ne 0 ]]; then
        echo "Installing zsh"
        brew install zsh
    fi
    
    echo "Checking if antigen is installed..."
    if ! hash antigen 2>/dev/null; then
        echo "Installing antigen"
        brew install antigen
    fi
    
    echo "Checking if kitty is installed..."
    if ! hash kitty 2>/dev/null; then
        echo "Installing kitty"
        curl -L https://sw.kovidgoyal.net/kitty/installer.sh | sh /dev/stdin
    fi

    echo "Checking if asdf is installed..."
    if ! hash asdf 2>/dev/null; then
        echo "Installing asdf"
        brew install asdf
    fi

    echo "Checking if python is installed..."
    if ! hash python 2>/dev/null; then
        echo "Installing python"
        brew install python@3.9
    fi

    echo "Checking if github client is installed..."
    if ! hash python 2>/dev/null; then
        echo "Installing github client"
        echo "  More info: https://formulae.brew.sh/formula/gh)"
        brew install gh
    fi

    echo "Checking if sdkman is installed..."
    if ! hash sdk 2>/dev/null; then
        echo "Installing sdkman"
        echo "  More info: https://sdkman.io/install"
        curl -s "https://get.sdkman.io" | bash
    fi
    
    
    echo "Installing fonts..."
    ./install-fonts.sh
    
    ###############################
    echo "Installing custom shell plugins..."
    
    #Install colorls
    #  colorls requires Ruby so install ruby :(
    local RBENV_VERSION="2.7.1"
    check_version "rbenv" "rbenv version | cut -d' ' -f1" ${RBENV_VERSION}
    
    if [[ "$VERSIONCHECK_RESULT" -ne 0 ]]; then
        echo "Installing ruby for colorls"
        brew update
        brew install ruby-build
        brew install rbenv
        rbenv install ${RBENV_VERSION}
        rbenv global ${RBENV_VERSION}
    else
        echo "ruby rbenv is already at proper version: $RBENV_VERSION"
    fi
    export PATH="$HOME/.rbenv/shims:$PATH"
    echo "Ruby version: $(ruby -v)"
    
    #Colorls 
    gem install --user-install colorls
    ###############################


    #INSTALL: asdf
    # TODO: hack
    echo "Installing asdf..."
    cp $DIR/dotfiles/.tool-versions $HOME/

    cd $HOME
    # https://github.com/asdf-vm/asdf/issues/1254
    awk '{ system("asdf plugin-add " $1) }' < .tool-versions 
    asdf install
    cd -
    ###############################

    
    echo "complete" > "${ENV_SETUP_STATUS}"
}

function determine_platform {
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

function remove-stale-scripts {
  local scripts_rm_dir="$HOME_LINUXENV_DIR/scripts/"
  local scripts_backup_dir="$HOME/_stale_linuxenv_scripts/"
  mkdir -p $scripts_backup_dir

  #Remove leading spaces with awk: https://unix.stackexchange.com/a/205854/189441
  # This did not work for subdirectories of scripts_rm_dir
  #local scripts_to_rm=($(diff -qr "$scripts_rm_dir" "$DIR/scripts/" | grep "^Only in $scripts_rm_dir" | cut -d: -f2- | awk '{$1=$1;print}' | while read line; do echo "$scripts_rm_dir/$line"; done))
  local scripts_to_rm=($(diff -qr "$scripts_rm_dir" "$DIR/scripts/" | grep "^Only in $scripts_rm_dir" | sed 's/Only in //g' | sed 's/: /\//g'))

  if [ ${#scripts_to_rm[@]} -ne 0 ]; then
      echo "Recognized scripts that are only present in $HOME_LINUXENV_DIR. Going to move them to $scripts_backup_dir"
      for script in $scripts_to_rm;
      do
        mv $script $scripts_backup_dir/
      done
  fi
}

function setup-vars-aliases {
  # !!! THE ORDER OF THE FOLLOWING SOURCE COMMANDS ARE STRICT !!!
    #source and add to path happens from $WORKPLACE_SPECIFIC_DIR/**
    source_single_file "${HOME_LINUXENV_DIR}/scripts/load-these-first.sh"
    source_single_file "${HOME_LINUXENV_DIR}/setup-vars.sh"
    source_scripts ${HOME_LINUXENV_DIR}/aliases
    source_scripts ${HOME_LINUXENV_DIR}/scripts
    source_files ".source-this"
    add_to_path ".add-to-path" "$WORKPLACE_SPECIFIC_DIR"
    add_to_path_directly ${HOME_LINUXENV_DIR}/scripts/python
    add_to_path_directly ${HOME_LINUXENV_DIR}/scripts/git
    add_to_path_directly $HOME/jetbrains-scripts/
}


function copy_files_from_linuxenv_repo_to_home {
    declare -a COPY_LIST=()
    
    #Bash
    COPY_LIST+=("$DIR/.bashrc $HOME/.bashrc")
    COPY_LIST+=("$DIR/.bash_profile $HOME/.bash_profile")
    
    #Zsh
    COPY_LIST+=("$DIR/.zshrc $HOME/.zshrc")
    COPY_LIST+=("$DIR/.zprofile $HOME/.zprofile")
    
    #Common
    COPY_LIST+=("$DIR/setup-vars.sh $HOME_LINUXENV_DIR/setup-vars.sh")
    COPY_LIST+=("$DIR/setup-env.sh $HOME_LINUXENV_DIR/setup-env.sh")
    COPY_LIST+=("$DIR/reset-env.sh $HOME_LINUXENV_DIR/reset-env.sh")
    COPY_LIST+=("$DIR/dotfiles/. $HOME/")
    COPY_LIST+=("$DIR/aliases/. $HOME_LINUXENV_DIR/aliases/")
    COPY_LIST+=("$DIR/scripts/. $HOME_LINUXENV_DIR/scripts")
    COPY_LIST+=("$DIR/scripts/python/. $HOME_LINUXENV_DIR/scripts/python")

    # TODO Dummy + error-prone way of adding all dirs manually --> Instead, implement exceptions e.g. workplace-specific/cloudera/investigations should not be copied
    # Old definition
    # COPY_LIST+=("$DIR/workplace-specific/. $WORKPLACE_SPECIFIC_DIR")

    COPY_LIST+=("$DIR/workplace-specific/cloudera/aliases/. $WORKPLACE_SPECIFIC_DIR/cloudera/aliases")
    COPY_LIST+=("$DIR/workplace-specific/cloudera/config/. $WORKPLACE_SPECIFIC_DIR/cloudera/config")
    COPY_LIST+=("$DIR/workplace-specific/cloudera/scripts/. $WORKPLACE_SPECIFIC_DIR/cloudera/scripts")
    COPY_LIST+=("$DIR/.npmrc $HOME/.npmrc")
    
    #Kitty conf + theme
    COPY_LIST+=("$DIR/config/kitty.conf $HOME/.config/kitty/kitty.conf")
    COPY_LIST+=("$DIR/config/theme.conf $HOME/.config/kitty/theme.conf")
    
    #Can't use is-platform-macos alias here as it's not yet loaded
    if [[ ! ${platform} == 'macOS' ]]; then
        COPY_LIST+=("$DIR/dotfiles/i3/. $HOME/.i3/")
    else
        printf_debug "$INFO_PREFIX Skip copying i3 files as platform is $platform"
    fi
    
    #set -e
    # printf_debug "Copying files, copy list: ${COPY_LIST[@]}"
    print_debug "Copying files, copy list:`printf '%s\n' "${COPY_LIST[@]}"`"
    copy_files "${COPY_LIST[@]}"
    #set +e
}

function setup-pythonpath {
  cd /Users/snemeth/development/cloudera/cde/dex
  echo "Setting up PYTHONPATH from dir: $(pwd)"
  asdf_python=$(asdf where python)
  ASDF_PYTHON_LIBS=$(find $asdf_python -type d -name "site-packages")
  STANDARD_PYTHON_LIBS="$HOME/Library/Python/3.8/lib/python/site-packages/"
  export PYTHONPATH="$STANDARD_PYTHON_LIBS:$ASDF_PYTHON_LIBS:${HOME_LINUXENV_DIR}/scripts/python/:$PYTHONPATH"
  popd
}

function linuxenv-initial-setup-mark-incomplete {
    rm $HOME_ENV/.initial-setup-status
}


#####################################
initial_setup
setup-pythonpath
remove-stale-scripts

# Define LINUXENV_* vars
LINUXENV_DEBUG="${LINUXENV_DEBUG:-0}"
export LINUXENV_DEBUG_YARNDEVTOOLS="${LINUXENV_DEBUG_YARNDEVTOOLS:-0}"
LINUXENV_SKIP_COPY="${LINUXENV_SKIP_COPY:-0}"

if [[ $LINUXENV_SKIP_COPY == 0 ]]; then
  copy_files_from_linuxenv_repo_to_home
else
  echo "NOTE: Skip copying files from linuxenv repo."
fi

setup-vars-aliases
set +x