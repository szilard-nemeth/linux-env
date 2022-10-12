#!/usr/bin/env bash

function ensure-command-available() {
    cmd="$1"
    command -v ${cmd} > /dev/null 2>&1
    
    if [[ $? -ne 0 ]]; then
        print_debug "$INFO_PREFIX $cmd aliases won't be used as command '$cmd' is not yet installed!"
        return 1
    fi
}

function is-platform-macos() {
    if [[ ${platform} == 'macOS' ]]; then
        return 0
    fi
}

function is-platform-linux() {
    if [[ ${platform} == 'linux' ]]; then
        return 0
    fi
}

function start-app-silently() {
    APP_NAME=$1
    nohup ${APP_NAME}& > /dev/null 2>&1
}