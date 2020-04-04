#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd $DIR

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
alias sl="sl --help" # steam-locomotive: https://www.cyberciti.biz/tips/displays-animations-when-accidentally-you-type-sl-instead-of-ls.html
alias grep='grep --color=auto'
alias dfh='df -h'
alias bashrc='vim ~/.bashrc'
alias logs="find /var/log -type f -exec file {} \; | grep 'text' | cut -d' ' -f1 | sed -e's/:$//g' | grep -v '[0-9]$' | xargs tail -f"
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

## ls ALIASES
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'


## OTHER ALIASES
# Add an "alert" alias for long running commands.  Use like so:
# sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'
eval $(thefuck --alias)
alias mc='LANG=en_EN.UTF-8 mc'

#TODO create alias: resync all changes from linuxenv repo (copies all files)
#TODO make this a function
alias zip-files="sudo find / -iname *1564501696813_0001_01_000001* -print0 | sudo tar -czvf backup-1564501696813_0001-20190730.tar.gz --null -T -"