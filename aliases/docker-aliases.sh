#!/usr/bin/env bash

command -v docker;
if [ $? -ne 0 ]; then
    echo "$INFO_PREFIX docker aliases won't be used as docker is not yet installed!"
    return 1
fi

alias docker-rm-net="docker network rm $(docker network ls | awk '/ / { print $1 }')"
alias docker-rmfv-all="docker-operation-except $DIR/.docker-op-exceptions rm -fv"
alias docker-rmf-all="docker-operation-except $DIR/.docker-op-exceptions rm -f"
alias docker-stop-all="docker-operation-except $DIR/.docker-op-exceptions stop"
alias docker-rmfv-all="docker rm -fv \$(docker ps -q)"

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