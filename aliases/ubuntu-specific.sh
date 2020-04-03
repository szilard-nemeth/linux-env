#!/usr/bin/env bash

#TODO create common function for this: is-os-mac, is-os-linux
if [[ ! ${platform} == 'linux' ]]; then
    echo "$INFO_PREFIX ubuntu-specific aliases won't be used as platform is $platform!"
    return 1
fi

alias intellij-keyboard-fix="ibus-daemon -rd"
alias suspend='sudo pm-suspend'
alias restart-network="sudo service network-manager restart"
alias konsoleb="konsole --background-mode&"
