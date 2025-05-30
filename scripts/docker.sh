#!/usr/bin/env bash

if ! ensure-command-available "docker"
then
    return 1
fi

function docker-execbash {
    containerid=`docker ps | grep $1 | cut -d ' ' -f 1`
    docker exec -it ${containerid} bash
}

function cleanup_docker_images {
  #docker rm --force $(docker ps --all --quiet) # remove all docker processes
  docker rmi $(docker images --filter dangling=true --quiet) # clean dangling docker images
}

function cleanup_docker_volumes {
  docker volume ls -qf dangling=true | xargs -r docker volume rm
}

function docker-operation-except {
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

function docker-rm-all-for-img {
  docker ps -a | awk '{ print $1,$2 }' | grep $1 | awk '{print $1 }' | xargs -I {} docker rm {}
}

function docker-listmounts {
  docker inspect -f '{{ .Mounts }}' $1
}

function docker-cleanup-guidance {
    echo "GENERIC CLEANUP COMMANDS:"
    echo "docker system df"
    echo "docker image prune"
    echo "docker container prune"
    echo "docker system prune --force"
    echo "docker system df"

    echo; echo "Delete first 80 images: "
    echo "docker images | awk '{print $3}' | tail -n 80 | xargs docker rmi"

    echo; echo "Delete Docker images with grepping for image name" 
    echo "docker images | grep \"DEX-9645\|DEX-7712\|DEX-7051\" | awk '{print \$3}' | xargs docker rmi"
    echo "docker images | grep 1.19.0-dev | awk '{print \$3}' | xargs docker rmi"
    echo "docker images | grep \"DEX-\" | grep -v \"DEX-7325\" | awk '{print \$3}' | xargs docker rmi -f"

    echo; echo "Delete Docker images by grepping for multiple CDE releases:"
    echo "docker images | grep \"1.21\|1.22.0\|1.20.3\"| awk '{print \$3}' | xargs docker rmi -f"

    echo; echo "REMOVE ALL DEX IMAGES (BE CAREFUL!):"
    echo "docker images | grep \"dex\" | awk '{print \$3}' | xargs docker rmi -f"

    echo; echo "REMOVE ALL THUNDERHEAD IMAGES (BE CAREFUL!):"
    echo "docker images | grep \"thunderhead\" | awk '{print \$3}' | xargs docker rmi -f"

    # https://forums.docker.com/t/simple-script-needed-to-delete-all-docker-images-over-4-weeks-old/28558/6    
    echo; echo "REMOVE IMAGES OLDER THAN DATE (3 weeks):"
    echo "docker image prune --all --filter \"until=504h\""
    echo "docker rmi \$(docker images --filter \"dangling=true\" -q --no-trunc)"

    echo; echo "More time based commands: "
    echo "https://dirask.com/posts/Docker-remove-images-older-than-some-specific-period-of-time-DnzWbD"
}