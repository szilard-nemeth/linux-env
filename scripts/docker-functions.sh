#!/usr/bin/env bash

function docker-execbash() {
    containerid=`docker ps | grep $1 | cut -d ' ' -f 1`
    docker exec -it $containerid bash
}