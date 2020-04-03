#!/usr/bin/env bash
if [[ ! ${platform} == 'linux' ]]; then
    echo "$INFO_PREFIX ubuntu-specific aliases won't be used as platform is $platform!"
    return 1
fi

function unmount-poweroff() {
#    sudo umount $1 && udisksctl power-off -b $1
     sudo udisksctl unmount -b $1 && sudo udisksctl power-off -b $1
}

alias suspend='sudo pm-suspend'
alias restart-network="sudo service network-manager restart"
alias konsoleb="konsole --background-mode&"
