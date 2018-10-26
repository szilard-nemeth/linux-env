#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd $DIR

#TODO create functions from scripts/*.sh

## LINUX-ENV ALIASES
alias goto-linuxenv-repo="cd $LINUX_ENV_REPO"
alias linux-env-reload="$LINUX_ENV_REPO/setup-env.sh"
alias linux-env-todos="grep '#TODO' -r $LINUX_ENV_REPO"

## OTHER ALIASES
alias rm='safe-rm'
alias intellij-keyboard-fix="ibus-daemon -rd"
alias currentweek="date +%V"
alias vpn-szyszy="sudo openvpn --client --config ~/openvpn-szyszy/client.ovpn --ca ~/openvpn-szyszy/ca.crt"

## CD-RELATED ALIASES
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
