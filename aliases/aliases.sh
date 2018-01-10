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

function unmount-poweroff() {
#    sudo umount $1 && udisksctl power-off -b $1
     sudo udisksctl unmount -b $1 && sudo udisksctl power-off -b $1
}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd $DIR

alias goto-linuxenv-repo="cd $LINUX_ENV_REPO"
alias intellij-keyboard-fix="ibus-daemon -rd"


command -v docker;
if [ $? -eq 0 ]; then
    alias docker-rm-net="docker network rm $(docker network ls | awk '/ / { print $1 }')"
    alias docker-rmfv-all="docker-operation-except $DIR/.docker-op-exceptions rm -fv"
    alias docker-rmf-all="docker-operation-except $DIR/.docker-op-exceptions rm -f"
    alias docker-stop-all="docker-operation-except $DIR/.docker-op-exceptions stop"
fi

#alias docker-rmfv-all="docker rm -fv \$(docker ps -q)"
alias konsoleb="konsole --background-mode&"
alias currentweek="date +%V"
alias vpn-szyszy="sudo openvpn --client --config ~/openvpn-szyszy/client.ovpn --ca ~/openvpn-szyszy/ca.crt"
alias aws-login="\$(aws ecr get-login --region eu-west-1)"
alias linux-env-reload="$LINUX_ENV_REPO/setup-env.sh"
alias restart-network="sudo service network-manager restart"

##i3 aliases

function i3-rename-window() {
  xdotool set_window --name "$1" `xdotool getactivewindow`
}

function i3-rename-workspace() {
  i3-input -F 'rename workspace to "%s"' -P 'New name: ' 2>&1 > /dev/null
}

alias i3-display-unplugged="xrandr --output HDMI1 --off"
alias i3-display-plugged="exec xrandr --output HDMI1 --auto --right-of eDP1"
alias i3-display-primary="xrandr --output HDMI1 --primary"
alias suspend="$HOME/i3/i3exit.sh suspend"

## cd aliases

up(){
  local d=""
  limit=$1
  for ((i=1 ; i <= limit ; i++))
    do
      d=$d/..
    done
  d=$(echo $d | sed 's/^\///')
  if [ -z "$d" ]; then
    d=..
  fi
  cd $d
}

#rsync aliases
alias rsync-backup="rsync -avh $HOME/backup/ /media/snemeth/szyszy-exthdd-data/backups/hell-laptop-backupsdir/"
