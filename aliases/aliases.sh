#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd $DIR

#TODO create alias: resync all changes from linuxenv repo (copies all files)
#TODO check all .sh under /aliases: Functions should be moved to /scripts

## LINUX-ENV ALIASES
alias goto-linuxenv-repo="cd $LINUX_ENV_REPO"
alias linux-env-reload="$LINUX_ENV_REPO/setup-env.sh"
alias linux-env-todos="grep '#TODO' -r $LINUX_ENV_REPO"

## OTHER ALIASES
alias rm='safe-rm'
alias intellij-keyboard-fix="ibus-daemon -rd"
alias currentweek="date +%V"
alias vpn-szyszy="sudo openvpn --client --config ~/openvpn-szyszy/client.ovpn --ca ~/openvpn-szyszy/ca.crt"
alias formatted-date="date +%Y%m%d_%H_%M_%S"
alias zip-files="sudo find / -iname *1564501696813_0001_01_000001* -print0 | sudo tar -czvf backup-1564501696813_0001-20190730.tar.gz --null -T -"
alias git-commits-above-master="git log --oneline HEAD ^master | wc -l"

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
