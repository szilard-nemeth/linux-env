#!/bin/bash

function docker-operation-except() {
    FILENAME="$1";
    shift;
    DOCKER_COMMAND="$@";

    EXCEPTION_NAMES="";
    GREP_CRITERIA="-v -E ";
    while IFS='' read -r line || [[ -n "$line" ]]; do
        EXCEPTION_NAMES+="$line ";

        GREP_CRITERIA+=".*$line.*|"
        done < $FILENAME;

    echo "Removing containers except names like: $EXCEPTION_NAMES"
    #Remove the last pipe
    GREP_CRITERIA=${GREP_CRITERIA::-1}


    CONTAINERS_TO_REMOVE=`docker ps --format '{{.ID}} {{.Names}}' | grep $GREP_CRITERIA`
    echo "These containers will be removed: "
    echo "$CONTAINERS_TO_REMOVE";
    docker ps --format '{{.Names}}' | grep $GREP_CRITERIA | xargs docker $DOCKER_COMMAND
}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

alias goto-linuxenv-repo="cd $HOME/development/my-repos/linux_env"
alias intellij-keyboard-fix="ibus-daemon -rd"

#alias docker-rmfv-all="docker rm -fv \$(docker ps -q)"
alias docker-rmfv-all="docker-operation-except $DIR/.docker-op-exceptions rm -fv"
alias docker-rmf-all="docker-operation-except $DIR/.docker-op-exceptions rm -f"
alias docker-stop-all="docker-operation-except $DIR/.docker-op-exceptions stop"
alias konsoleb="konsole --background-mode&"
alias currentweek="date +%V"
alias vpn-szyszy="sudo openvpn --client --config ~/openvpn-szyszy/client.ovpn --ca ~/openvpn-szyszy/ca.crt"
alias aws-login="\$(aws ecr get-login --region eu-west-1)"
alias linux-env-reload="~/development/my-repos/linux_env/setup-env.sh"

##i3 aliases

function i3-rename-window() {
  xdotool set_window --name "$1" `xdotool getactivewindow`
}

function i3-rename-workspace() {
  i3-input -F 'rename workspace to "%s"' -P 'New name: ' 2>&1 > /dev/null
}

alias i3-display-unplugged="xrandr --output HDMI1 --off"
alias i3-display-plugged="exec xrandr --output HDMI1 --auto --right-of eDP1"

