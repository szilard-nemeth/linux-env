#!/usr/bin/env bash

function docker-execbash() {
    containerid=`docker ps | grep $1 | cut -d ' ' -f 1`
    docker exec -it $containerid bash
}

cleanup_docker_images() {
  #docker rm --force $(docker ps --all --quiet) # remove all docker processes
  docker rmi $(docker images --filter dangling=true --quiet) # clean dangling docker images
}

cleanup_docker_volumes() {
  docker volume ls -qf dangling=true | xargs -r docker volume rm
}