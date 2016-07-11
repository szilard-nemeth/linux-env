#setup locations
HELLMANN_DEV_ROOT="$HOME/development/hellmann-repos/"
TRACKING_ROOT="$HELLMANN_DEV_ROOT/trackingall/"
TRACKING_DOCKER_COMPOSE_ROOT="$TRACKING_ROOT/tracking-docker/tracking-docker-compose/tracking/"
RLR_ROOT="$HELLMANN_DEV_ROOT/rlr/"
RLR_DOCKER_COMPOSE_ROOT="$RLR_ROOT/rlr-docker-compose/rlr/"

#goto aliases
alias goto-tracking="cd $HELLMANN_DEV_ROOT/trackingall"
alias goto-rlr="cd $HELLMANN_DEV_ROOT/rlr"

#maven aliases
alias mvn-ci-skiptest="mvn clean install -DskipTests"
alias mvn-ci-skip-all="mvn clean install -DskipTests -Dnogwt -Dnodocker"

#docker aliases
#Tracking
alias docker-tracking-start-int-env="~/development/hellmann-repos/trackingall/build/start-integration-env.sh"
alias docker-tracking-start-env="$TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local tracking_1 up"
alias docker-tracking-stop-env="$TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local tracking_1 rm -fv"
#RLR
alias docker-rlr-start-int-env="$RLR_ROOT/build/start-db-env.sh"
alias docker-rlr-start-env="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local rlr_1 up"
alias docker-rlr-start-env="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local rlr_1 rm -fv"

