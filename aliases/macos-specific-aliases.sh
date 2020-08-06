#!/usr/bin/env bash

if ! is-platform-macos
then
    echo "Platform is not MacOS!"
    return 1
fi

#https://superuser.com/questions/1101311/how-many-cores-does-my-mac-have
alias get-cores="sysctl hw.physicalcpu hw.logicalcpu"