echo "$(date) -- .zshrc executed by shell: $0" >> $HOME/.zshrc.log

function setup-history() {  
    export HISTFILESIZE=1000000000          #How many lines of history to keep in memory
    export HISTSIZE=1000000000              #How many lines of history to keep in memory
    HISTFILE=~/.zsh_history                 #Where to save history to disk
    SAVEHIST=1000000000                     #Number of history entries to save to disk
    #HISTDUP=erase                           #Erase duplicates in the history file
    setopt HIST_FIND_NO_DUPS
    setopt HIST_IGNORE_ALL_DUPS
    setopt    appendhistory                 #Append history to the history file (no overwriting)
    setopt    sharehistory                  #Share history across terminals
    setopt    incappendhistory              #Immediately append to the history file, not just when a term is killed
}

function setup() {
    # If set, the pattern "**" used in a pathname expansion context will
    # match all files and zero or more directories and subdirectories.
    # shopt -s globstar
    
    # make less more friendly for non-text input files, see lesspipe(1)
    [[ -x /usr/bin/lesspipe ]] && eval "$(SHELL=/bin/sh lesspipe)"
    
    setup-key-bindings
    setup-history
    setup-antigen
    setup-prompt
    setup-kitty
    setup-sdkman
    setup-tab-title
}

function setup-antigen() {
    #Load antigen
    source $(brew --prefix)/share/antigen/antigen.zsh
    
    # Load the oh-my-zsh's library.
    antigen use oh-my-zsh
    
    # Bundles from the default repo (robbyrussell's oh-my-zsh).
    antigen bundle git
    antigen bundle pip
    antigen bundle lein
    antigen bundle command-not-found
    
    # Syntax highlighting bundle.
    antigen bundle zsh-users/zsh-syntax-highlighting
    
    # Load the Spaceship theme.
    antigen theme denysdovhan/spaceship-prompt
    
    # https://github.com/trystan2k/zsh-tab-title
    antigen bundle trystan2k/zsh-tab-title

    # Tell Antigen that you're done.
    antigen apply
}

setup-prompt() {
    echo "Setting up prompt..."
    #EXAMPLE OLD PROMPT:
    # szilardnemeth@snemeth-MBP[19:14:36] <0> @master )--( ~/development/my-repos/linux-env )
    
    SPACESHIP_PROMPT_ORDER=(
      user          # Username section
      host          # Hostname section
      time          # Time stamps section
      exit_code     # Exit code section
      battery       # Battery level and status
      dir           # Current directory section

      git           # Git section (git_branch + git_status)
      #hg            # Mercurial section (hg_branch  + hg_status)
      package       # Package version
      node          # Node.js section
      ruby          # Ruby section
      #elixir        # Elixir section
      #xcode         # Xcode section
      #swift         # Swift section
      golang        # Go section
      #php           # PHP section
      #rust          # Rust section
      #haskell       # Haskell Stack section
      #julia         # Julia section
      docker        # Docker section
      aws           # Amazon Web Services section
      gcloud        # Google Cloud Platform section
      venv          # virtualenv section
      #conda         # conda virtualenv section
      #pyenv         # Pyenv section
      #dotnet        # .NET section
      #ember         # Ember.js section
      kubectl       # Kubectl context section
      #terraform     # Terraform workspace section
      exec_time     # Execution time
      line_sep      # Line break
      vi_mode       # Vi-mode indicator
      jobs          # Background jobs indicator
      char          # Prompt character
    )
    
    #Generic
    SPACESHIP_PROMPT_DEFAULT_PREFIX=""
    
    #Username
    SPACESHIP_USER_SHOW="always"
    SPACESHIP_USER_PREFIX=" "
    SPACESHIP_USER_SUFFIX=""
    
    #Host
    SPACESHIP_HOST_SHOW="always"
    SPACESHIP_HOST_PREFIX="@"
    
    #Time
    SPACESHIP_TIME_SHOW=true
    SPACESHIP_TIME_PREFIX="["
    SPACESHIP_TIME_SUFFIX="] "
    
    #Exit code
    SPACESHIP_EXIT_CODE_SHOW="true"
    SPACESHIP_EXIT_CODE_SYMBOL=""
    SPACESHIP_EXIT_CODE_PREFIX="<"
    SPACESHIP_EXIT_CODE_SUFFIX="> "
    
    #Battery
    SPACESHIP_BATTERY_SHOW="always"
    
    #Dir
    SPACESHIP_DIR_PREFIX="--( "
    SPACESHIP_DIR_SUFFIX=" ) "
    SPACESHIP_DIR_TRUNC=0
    SPACESHIP_DIR_TRUNC_REPO="false"
    
    #Git
    SPACESHIP_GIT_PREFIX=""
    SPACESHIP_GIT_BRANCH_PREFIX="@"
    
    #Docker
    SPACESHIP_DOCKER_PREFIX=""
}

function setup-tab-title {
    # https://github.com/trystan2k/zsh-tab-title
    export DISABLE_AUTO_TITLE="true"
    export ZSH_TAB_TITLE_ENABLE_FULL_COMMAND=true
    export ZSH_TAB_TITLE_PREFIX=""
}

function setup-kitty() {
    echo "Setting up kitty..."
    autoload -Uz compinit
    compinit
    # Completion for kitty
    kitty + complete setup zsh | source /dev/stdin
}

function setup-sdkman() {
    if [ -f "$HOME/.sdkman/bin/sdkman-init.sh" ]; then
        echo "Setting up sdkman..."
        source "$HOME/.sdkman/bin/sdkman-init.sh"
    else
        echo "WARN: sdkman init script does not exist at: $HOME/.sdkman/bin/sdkman-init.sh"
    fi
}


function setup-key-bindings() {
    bindkey "^[[1;3C" forward-word
    bindkey "^[[1;3D" backward-word
}

function print-welcome-screen() {
    echo "";
    echo "WELCOME"
    cal;
    echo -ne "Sysinfo: ";uptime;
    echo "";
}

function set_debug() {
    HOME_ENV="$HOME/.env/"
    ENV_DEBUG_SETUP_FILE="$HOME_ENV/.debug-setup"
    if [[ ! -f ${ENV_DEBUG_SETUP_FILE} ]]; then
        touch ${ENV_DEBUG_SETUP_FILE}
    fi
    
    local state=$(cat ${ENV_DEBUG_SETUP_FILE} | head -n1 | tr -d '[:space:]')
    if [[ "$state" == 'enabled' ]]; then
        echo "Enabling debug printouts for setup"
        ENABLE_DEBUG=1
    else
        ENABLE_DEBUG=0
    fi
}

function run-setup-scripts() {
    LINUX_ENV_REPO=$HOME/development/my-repos/linux-env/
    SETUP_ENV_SCRIPT=${LINUX_ENV_REPO}/setup-env.sh
    
    if [[ -d ${LINUX_ENV_REPO} ]]; then
        LINUX_ENV_REPO=$HOME/development/my-repos/linux-env/
        export LINUX_ENV_REPO
        # Source setup env from linux-env repository (copying all env files)
        echo "Running setup-env.sh..."
        if [[ $ENABLE_DEBUG -eq 1 ]]; then
            set -x
            setopt XTRACE
            . ${LINUX_ENV_REPO}/setup-env.sh
        else
            . ${LINUX_ENV_REPO}/setup-env.sh
        fi
    else
        echo "Tried to source ${SETUP_ENV_SCRIPT}, but linux-env repo does not exist. Please clone the repository!" 
    fi
}

#################################################################################

### Uncomment these to run setup scripts on every shell launch
setup
set_debug
run-setup-scripts
export SKIP_LINUXENV_COPY=1



print-welcome-screen