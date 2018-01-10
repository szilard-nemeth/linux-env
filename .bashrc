# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
[ -z "$PS1" ] && return

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
##empty value --> unlimited
HISTSIZE=
HISTFILESIZE=

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "$debian_chroot" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	# We have color support; assume it's compliant with Ecma-48
	# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
	# a case would tend to support setf rather than setaf.)
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto --group-directories-first'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if [ -f /etc/bash_completion ] && ! shopt -oq posix; then
    . /etc/bash_completion
fi

LIGHTRED="$(tput bold ; tput setaf 1)"
LIGHTGREEN="$(tput bold ; tput setaf 2)"
YELLOW="$(tput bold ; tput setaf 3)"
LIGHTBLUE="$(tput bold ; tput setaf 4)"
LIGHTPURPLE="$(tput setaf 5)"
LIGHTCYAN="$(tput bold ; tput setaf 6)"
WHITE="$(tput bold ; tput setaf 7)"
NOCOLOR='\[\033[0m\]'

# Prompt
# ------

# Start with a newline as some commands don't end their output with one
PS1="\n$WHITE┌-("

# username@hostname[hh:mm:ss]
PS1="$PS1 \u@$YELLOW\h$WHITE[\t]"

# Exit code of the latest command: green "<0>" or red ">NON-ZERO<"
PS1="$PS1 \$(__x=\$?; if [[ \$__x -ne 0 ]]; then"
PS1="$PS1 echo -n \"$LIGHTRED>\$__x<\";"
PS1="$PS1 else echo -n \"$LIGHTGREEN<\$__x>\"; fi)"

# Last max 30 characters of current working directory with a less-than sign
# when truncated
#PS1="$PS1 $LIGHTPURPLE"
#PS1="$PS1\$(echo '\w' | sed -r 's/^.*.(.{30})/<\1/')"

# Display battery info if available
PS1="$PS1$LIGHTCYAN\$(acpi -b 2>/dev/null |"
PS1="$PS1 sed -r 's/^.*(: ([a-z])[a-z]*, ([0-9]*%)).*\$/ [\\2\\3]/i' |"
PS1="$PS1 grep --color=never -m1 '^ \\\\[.*\\\\]\$')"

# When inside a git repo, display the name of the current working branch
PS1="$PS1$LIGHTBLUE\$(git branch 2>/dev/null | grep -m1 --color=never '^[*] '"
PS1="$PS1 | sed 's/^[*] / @/')"

# New command to be entered in a new line
PS1="$PS1 $WHITE)--( $LIGHTPURPLE"
PS1="$PS1\$(echo '\w' | sed -r 's/^.*.(.{90})/<\1/')"
PS1="$PS1 $WHITE)--\n└-\\\$ $NOCOLOR"

# Adjust the title of the terminal window
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;\$PROMPT_EXTRA \u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

setproxy(){
	if [[ -z "$http_proxy" ]];
	then export http_proxy=http://159.107.0.62:8080;export https_proxy=http://159.107.0.62:8080;echo "e/// proxy on";
	else unset http_proxy;unset https_proxy;echo "e/// proxy off";
	fi
}

svim(){
sudo vim -u /home/$USER/.vimrc $1
}

extract () {
     if [ -f $1 ] ; then
         case $1 in
             *.tar.bz2)   tar xjf $1        ;;
             *.tar.gz)    tar xzf $1     ;;
             *.bz2)       bunzip2 $1       ;;
             *.rar)       rar x $1     ;;
             *.gz)        gunzip $1     ;;
             *.tar)       tar xf $1        ;;
             *.tbz2)      tar xjf $1      ;;
             *.tgz)       tar xzf $1       ;;
             *.zip)       unzip $1     ;;
             *.Z)         uncompress $1  ;;
             *.7z)        7z x $1    ;;
             *)           echo "'$1' cannot be extracted via extract()" ;;
         esac
     else
         echo "'$1' is not a valid file"
     fi
}

#netinfo - shows network information for your system
netinfo ()
{
echo "--------------- Network Information ---------------"
/sbin/ifconfig | awk /'inet addr/ {print $2}'
/sbin/ifconfig | awk /'Bcast/ {print $3}'
/sbin/ifconfig | awk /'inet addr/ {print $4}'
/sbin/ifconfig | awk /'HWaddr/ {print $4,$5}'
echo "---------------------------------------------------"
}

#dirsize - finds directory sizes and lists them for the current directory
dirsize ()
{
du -shx * .[a-zA-Z0-9_]* 2> /dev/null | \
egrep '^ *[0-9.]*[MG]' | sort -n > /tmp/list
egrep '^ *[0-9.]*M' /tmp/list
egrep '^ *[0-9.]*G' /tmp/list
rm -rf /tmp/list
}

psgrep() {
	if [ ! -z $1 ] ; then
		echo "Grepping for processes matching $1..."
		ps aux | grep $1 | grep -v grep
	else
		echo "!! Need name to grep for"
	fi
}

psgrep-silent() {
	if [ ! -z $1 ] ; then
		ps aux | grep $1 | grep -v grep
	else
		echo "!! Need name to grep for"
	fi
}

ANT_HOME=/usr/share/ant
JAVA_HOME=/usr/lib/jvm/java-8-oracle/
export JAVA_HOME
export ANT_HOME
PATH=$PATH:$ANT_HOME/bin
PATH=$PATH:$HOME/scripts/
PATH=$PATH:$HOME/.npm-global/bin
export PATH
export MAVEN_OPTS="-Xmx1024m -XX:MaxPermSize=1024m"
export ANT_OPTS="-XX:PermSize=512m -XX:MaxPermSize=512m -Xmx1024m -Xms1024m"

alias sl="sl --help"
alias gedit="vim"
alias grep='grep --color=auto'
alias dfh='df -h'
alias calc='gcalctool -s'

export GIT_EDITOR='vim'

#apt
alias install='sudo apt-get install'
alias uninstall='sudo apt-get remove'
alias reinstall='sudo apt-get --reinstall install'
alias remove='sudo apt-get remove'
alias purge='sudo apt-get remove --purge'
alias update='sudo apt-get update'
alias upgrade='sudo apt-get upgrade'
alias clean='sudo apt-get autoclean && sudo apt-get autoremove'
alias search='apt-cache search'
alias show='apt-cache show'
alias sources='(sudo vim /etc/apt/sources.list)'
alias go='sudo apt-get update && sudo apt-get upgrade && sudo apt-get autoclean && sudo apt-get autoremove'

alias bashrc='vim ~/.bashrc'

alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

bind '"\es"':"\"calc \""

# WELCOME SCREEN
################################################## #####

LIGHTGREEN="$(tput bold ; tput setaf 2)"

echo -e "${WHITE}"; cal ;
echo -ne "${CYAN}";
echo -ne "${LIGHTPURPLE}Sysinfo:";uptime ;echo ""

# source other alias files
#################################################################################

LINUX_ENV_REPO=$HOME/development/my-repos/linux_env/
export LINUX_ENV_REPO
#source setup env from linux_env repository (copying all env files)
. $LINUX_ENV_REPO/setup-env.sh

HOME_LINUXENV_DIR="$HOME/.linuxenv/"
CLOUDERA_DIR="$HOME_LINUXENV_DIR/workplace-specific/cloudera/"

export HOME_LINUXENV_DIR
export CLOUDERA_DIR

#eval $(thefuck --alias)
alias mc='LANG=en_EN.UTF-8 mc'