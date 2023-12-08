#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd $DIR

## LINUX-ENV ALIASES
alias linuxenv-reload="cp ~/development/my-repos/linux-env/setup-env.sh ~/.linuxenv/setup-env.sh && cp ~/development/my-repos/linux-env/.zshrc ~/ && LINUXENV_SKIP_COPY=0 LINUXENV_DEBUG=1 source ~/.linuxenv/setup-env.sh"
alias linuxenv-todos="grep '#TODO' -r $LINUX_ENV_REPO"
alias linuxenv-debug-on="echo \"enabled\" > ${ENV_DEBUG_SETUP_FILE}"
alias linuxenv-debug-off="echo \"disabled\" > ${ENV_DEBUG_SETUP_FILE}"
alias edit-linuxenv="subl ~/development/my-repos/linux-env/"
alias edit-run-configs="subl ~/development/my-repos/project-run-configurations/"
alias edit-branchcomparator-latest="subl ~/snemeth-dev-projects/yarn_dev_tools/latest-session-branchcomparator/"

## KNOWLEDGE BASE
alias edit-knowledgebase="subl ~/development/my-repos/knowledge-base"
alias edit-knowledgebase-private="subl ~/development/my-repos/knowledge-base-private"


## GOTO ALIASES
alias goto-linuxenv-repo="cd $LINUX_ENV_REPO"
alias goto-kb-repo="cd $KB_REPO"
alias goto-kb-private-repo="cd $KB_PRIVATE_REPO"
alias goto-pythoncommons="cd $PYTHON_COMMONS_REPO"
alias goto-yarndevtools="cd $YARNDEVTOOLS_REPO"


## GIT ALIASES
alias git-commits-above-master="git log --oneline HEAD ^master | wc -l"
alias git-mybranches="git branch | grep 'own-'"
alias git-commit-msg="git log -n 1 --pretty=format:%s"
alias git-remove-trailing-ws="git diff-tree --no-commit-id --name-only -r HEAD | xargs sed -i 's/[[:space:]]*$//'"
alias git-fix-author-info-private="git config user.email 'szilard.nemeth88@gmail.com' && git config user.name 'Szilard Nemeth' && git commit --amend --reset-author"
alias git-fix-author-info-cloudera="git config user.email 'snemeth@cloudera.com' && git config user.name 'Szilard Nemeth' && git commit --amend --reset-author"
alias git-add-all-tracked="git status -s | grep -v \"??\" | cut -c 4- | xargs git add"


#https://stackoverflow.com/a/40884093/1106893 --> 4b825dc642cb6eb9a060e54bf8d69288fbee4904 is the id of the "empty tree"
alias git-save-all-commits="rm /tmp/patches/*; git format-patch 4b825dc642cb6eb9a060e54bf8d69288fbee4904..HEAD -o /tmp/patches"
alias git-add-mod="git ls-files --modified | xargs git add"
alias gs="git status"
alias gc="git commit"
alias ga="git add"

## OTHER ALIASES
alias rm='safe-rm'
alias currentweek="date +%V"
alias vpn-szyszy="sudo openvpn --client --config ~/openvpn-szyszy/client.ovpn --ca ~/openvpn-szyszy/ca.crt"
alias date-formatted="date +%Y%m%d_%H%M%S"
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

#colorls
alias lc='colorls -lA --sd'

##Aliases for my DEV projects
#Assuming venv is in googlechrometoolkit repo's root

# Google chrome toolkit aliases + Python setup
GCHROME_TOOLKIT_ROOT="$HOME/development/my-repos/google-chrome-toolkit/"
GCHROME_TOOLKIT_MODULE_ROOT="$GCHROME_TOOLKIT_ROOT/googlechrometoolkit/"
GCHROME_TOOLKIT_VENV="$GCHROME_TOOLKIT_ROOT/venv/"
BIN_PYTHON_GCHROME="$GCHROME_TOOLKIT_VENV/bin/python3"
local SETUP_PYENV="PYTHONPATH=$GCHROME_TOOLKIT_ROOT:$PYTHONPATH"
alias save-tabs-android="$SETUP_PYENV $BIN_PYTHON_GCHROME $GCHROME_TOOLKIT_MODULE_ROOT/save_open_tabs_android.py"
alias save-chrome-history-all="$SETUP_PYENV $BIN_PYTHON_GCHROME $GCHROME_TOOLKIT_MODULE_ROOT/main.py --search-db-files --export-mode all"

alias myrepos-sync="myrepos_syncer.py"
alias gpwh="git-push-with-hooks.sh"

## OTHER ALIASES
# Add an "alert" alias for long running commands.  Use like so:
# sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'
eval $(thefuck --alias)
alias mc='LANG=en_EN.UTF-8 mc'

#TODO create alias: resync all changes from linuxenv repo (copies all files)
#TODO make this a function
alias zip-files="sudo find / -iname *1564501696813_0001_01_000001* -print0 | sudo tar -czvf backup-1564501696813_0001-20190730.tar.gz --null -T -"

#https://stackoverflow.com/a/49752003/1106893
alias zsh-printcolors="for code in {000..255}; do print -P -- "$code: %F{$code}Color%f"; done"
alias list-aliases-functions="print -rl -- ${(k)aliases} ${(k)functions} ${(k)parameters}"


###WHITESPACE PIPE TRICK: https://superuser.com/a/1503113
# SP  ' '  0x20 = · U+00B7 Middle Dot
# TAB '\t' 0x09 = ￫ U+FFEB Halfwidth Rightwards Arrow
# CR  '\r' 0x0D = § U+00A7 Section Sign (⏎ U+23CE also works fine)
# LF  '\n' 0x0A = ¶ U+00B6 Pilcrow Sign (was "Paragraph Sign")
alias whitespace="sed 's/ /·/g;s/\t/￫/g;s/\r/§/g;s/$/¶/g'"

alias copy-trello-checklist-script="cat ~/development/my-repos/knowledge-base/codesnippets/js-html-css/copy-trello-checklist-smartlinks.js | pbcopy"
alias copy-pushbullet-linksaver-script="cat ~/development/my-repos/knowledge-base/codesnippets/js-html-css/pushbullet-save-links.js | pbcopy"
alias svim='vim -u ~/.SpaceVim/vimrc'
alias link-to-project-run-configurations="ln -s ~/development/my-repos/project-run-configurations/pycharm/$PROJECT_TO_LINK/.run ./.run"

alias history="history 1 -1"
