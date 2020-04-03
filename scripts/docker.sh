#!/usr/bin/env bash

if ! ensure-command-available "docker"
then
    return 1
fi

function docker-execbash() {
    containerid=`docker ps | grep $1 | cut -d ' ' -f 1`
    docker exec -it ${containerid} bash
}

function cleanup_docker_images() {
  #docker rm --force $(docker ps --all --quiet) # remove all docker processes
  docker rmi $(docker images --filter dangling=true --quiet) # clean dangling docker images
}

function cleanup_docker_volumes() {
  docker volume ls -qf dangling=true | xargs -r docker volume rm
}

function docker-operation-except() {
    FILENAME="$1";
    shift;
    DOCKER_COMMAND="$@";

    EXCEPTION_NAMES="";
    GREP_CRITERIA="-v -E ";
    while IFS='' read -r line || [[ -n "$line" ]]; do
        EXCEPTION_NAMES+="$line ";

        GREP_CRITERIA+=".*$line.*|"
        done < ${FILENAME};

    echo "Removing containers except names like: $EXCEPTION_NAMES"
    #Remove the last pipe
    GREP_CRITERIA=${GREP_CRITERIA::-1}


    CONTAINERS_TO_REMOVE=`docker ps --format '{{.ID}} {{.Names}}' | grep ${GREP_CRITERIA}`
    echo "These containers will be removed: "
    echo "$CONTAINERS_TO_REMOVE";
    docker ps --format '{{.Names}}' | grep ${GREP_CRITERIA} | xargs docker ${DOCKER_COMMAND}
}