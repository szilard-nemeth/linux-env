#!/usr/bin/env bash

function svim(){
    sudo vim -u /home/${USER}/.vimrc $1
}

function debug-command() {
    local cmd=$1
    local grep_for=$2
    set -x;
    ${cmd} 2>&1; 
    set +x;
}