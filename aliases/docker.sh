#!/usr/bin/env bash

if ! ensure-command-available "docker"
then
    return 1
fi

alias docker-rm-net="docker network rm $(docker network ls | awk '/ / { print $1 }')"
alias docker-rmfv-all="docker-operation-except $DIR/.docker-op-exceptions rm -fv"
alias docker-rmf-all="docker-operation-except $DIR/.docker-op-exceptions rm -f"
alias docker-stop-all="docker-operation-except $DIR/.docker-op-exceptions stop"
alias docker-rmfv-all="docker rm -fv \$(docker ps -q)"
alias docker-rmf-dangling="docker images -f \"dangling=true\" -q | xargs docker rmi -f"