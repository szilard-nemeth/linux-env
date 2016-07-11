#setup locations
HELLMANN_DEV_ROOT="/home/snemeth/development/hellmann-repos/"
TRACKING_ROOT="$HELLMANN_DEV_ROOT/trackingall/"
RLR_ROOT="$HELLMANN_DEV_ROOT/rlr/"
TRACKING_DOCKER_COMPOSE_ROOT="$TRACKING_ROOT/tracking-docker/tracking-docker-compose/tracking/"
RLR_DOCKER_COMPOSE_ROOT="$RLR_ROOT/rlr-docker-compose/rlr/"


#goto aliases
alias goto-tracking="cd /home/snemeth/development/hellmann-repos/trackingall"
alias goto-rlr="cd /home/snemeth/development/hellmann-repos/rlr"

#maven aliases
alias mvn-st="mvn clean install -DskipTests"
alias mvn-skipall="mvn clean install -DskipTests -Dnogwt -Dnodocker"


#docker aliases
#Tracking
alias docker-tracking-start-int-env="~/development/hellmann-repos/trackingall/build/start-integration-env.sh"
alias docker-tracking-start-env="$TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local tracking_1 up"
alias docker-tracking-stop-env="$TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local tracking_1 rm -fv"
#RLR
alias docker-rlr-start-int-env="$RLR_ROOT/build/start-db-env.sh"
alias docker-rlr-start-env="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local rlr_1 up"
alias docker-rlr-start-env="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local rlr_1 rm -fv"

