#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd $DIR

KB_REPO="$HOME/development/my-repos/knowledge-base/"
KB_PRIVATE_REPO="$HOME/development/my-repos/knowledge-base-private/"

#TODO create alias: resync all changes from linuxenv repo (copies all files)

## LINUX-ENV ALIASES
alias linux-env-reload="$LINUX_ENV_REPO/setup-env.sh"
alias linux-env-todos="grep '#TODO' -r $LINUX_ENV_REPO"


## GOTO ALIASES
alias goto-linuxenv-repo="cd $LINUX_ENV_REPO"
alias goto-kb-repo="cd $KB_REPO"
alias goto-kb-private-repo="cd $KB_PRIVATE_REPO"


## GIT ALIASES
alias git-commits-above-master="git log --oneline HEAD ^master | wc -l"
alias git-mybranches="git branch | grep 'own-'"
alias git-commit-msg="git log -n 1 --pretty=format:%s"
alias git-remove-trailing-ws="git diff-tree --no-commit-id --name-only -r HEAD | xargs sed -i 's/[[:space:]]*$//'"


## OTHER ALIASES
alias rm='safe-rm'
alias currentweek="date +%V"
alias vpn-szyszy="sudo openvpn --client --config ~/openvpn-szyszy/client.ovpn --ca ~/openvpn-szyszy/ca.crt"
alias date-formatted="date +%Y%m%d_%H_%M_%S"

#TODO make this a function
alias zip-files="sudo find / -iname *1564501696813_0001_01_000001* -print0 | sudo tar -czvf backup-1564501696813_0001-20190730.tar.gz --null -T -"