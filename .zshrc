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
    
    setup-antigen
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
    
    # Tell Antigen that you're done.
    antigen apply
}

function print-welcome-screen() {
    cal;
    echo -ne "Sysinfo:";uptime;echo ""
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
setup-history
setup
print-welcome-screen
set_debug
run-setup-scripts