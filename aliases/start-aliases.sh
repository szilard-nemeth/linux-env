#!/usr/bin/env bash

INTELLIJ_PATH="/usr/local/intellij-idea6_3_3/bin/idea.sh"
SQUIRREL_PATH=/usr/local/squirrel/squirrel-sql.sh

start-app-silent() {
    APP_NAME=$1
    ##TODO store logs to file!
    nohup $APP_NAME& > /dev/null 2>&1
}

alias start-google-chrome="start-app-silent google-chrome"
alias start-intellij="start-app-silent $INTELLIJ_PATH"
alias start-squirrel="start-app-silent $SQUIRREL_PATH"
alias start-hipchat4="start-app-silent hipchat4"
##TODO why this is not working?
alias restart-hipchat4="psgrep-silent hipchat | awk '{print $2}' | xargs kill && start-hipchat4"
