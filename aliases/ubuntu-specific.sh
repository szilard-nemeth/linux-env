#!/usr/bin/env bash

if ! is-platform-linux
then
    echo "$INFO_PREFIX ubuntu-specific aliases won't be used as platform is $platform!"
    return 1
fi

alias intellij-keyboard-fix="ibus-daemon -rd"
alias suspend='sudo pm-suspend'
alias restart-network="sudo service network-manager restart"
alias konsoleb="konsole --background-mode&"


#APT ALIASES
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