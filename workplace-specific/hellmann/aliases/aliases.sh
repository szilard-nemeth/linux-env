#!/bin/bash

#setup locations
HELLMANN_DEV_ROOT="$HOME/development/hellmann-repos/"
HELLMANN_TT_ROOT="$HELLMANN_DEV_ROOT/gis-portal-trackandtrace/"

#Tracking
TRACKING_COMPOSE_NAME="tracking_1"
TRACKING_COMPOSE_ARGS="localhost local $TRACKING_COMPOSE_NAME"
TRACKING_ROOT="$HELLMANN_TT_ROOT/trackingall/"
TRACKING_DOCKER_COMPOSE_ROOT_TR="$TRACKING_ROOT/tracking-docker/tracking-docker-compose/tracking/"
TRACKING_DOCKER_COMPOSE_ROOT_TDS="$TRACKING_ROOT/tracking-docker/tracking-docker-compose/dataservice/"
TRACKING_DOCKER_COMPOSE_ROOT_KAFKA="$TRACKING_ROOT/tracking-docker/tracking-docker-compose/kafka-feeder/"

#Road Live Reporting
RLR_ROOT="$HELLMANN_TT_ROOT/rlr/"
RLR_DOCKER_COMPOSE_ROOT="$RLR_ROOT/rlr-docker-compose/rlr/"
RLR_COMPOSE_NAME="rlr_1"
RLR_COMPOSE_ARGS="localhost local $RLR_COMPOSE_NAME"



#alias functions
mavenSetVersion() {
	mvn versions:set -DnewVersion=$1
}

alias mount-allshare="sudo mount.cifs //172.24.227.38/ALLSHARE /mnt/allshare/ -o user=snemeth"

#goto aliases
alias goto-tracking="cd $TRACKING_ROOT"
alias goto-rlr="cd $RLR_ROOT"
alias goto-deploy="cd $HOME/development/hellmann-repos/gis-portal-portalservices/hps-deploy"
alias goto-thinpoc="cd $HOME/development/hellmann-repos/gis-portal-applications/thinpoc"

#maven aliases
alias mvn-ci="mvn clean install"
alias mvn-ci-skiptest="mvn clean install -DskipTests"
alias mvn-ci-skip-all="mvn clean install -DskipTests -Dnogwt -Dnodocker"
alias mvn-setversion=mavenSetVersion

#docker aliases
#Tracking
alias docker-tracking-start-integration="$TRACKING_ROOT/build/start-integration-env.sh"
alias docker-tracking-start="$TRACKING_DOCKER_COMPOSE_ROOT_TR/call-compose.sh $TRACKING_COMPOSE_ARGS up -d && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_TDS/call-compose.sh $TRACKING_COMPOSE_ARGS up -d && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_KAFKA/call-compose.sh $TRACKING_COMPOSE_ARGS up -d;"

alias docker-tracking-start-dataservice="$TRACKING_DOCKER_COMPOSE_ROOT_TDS/call-compose.sh $TRACKING_COMPOSE_ARGS up -d"

alias docker-tracking-stop="$TRACKING_DOCKER_COMPOSE_ROOT_TR/call-compose.sh $TRACKING_COMPOSE_ARGS kill && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_TR/call-compose.sh $TRACKING_COMPOSE_ARGS rm -f && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_TDS/call-compose.sh $TRACKING_COMPOSE_ARGS kill && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_TDS/call-compose.sh $TRACKING_COMPOSE_ARGS rm -f && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_KAFKA/call-compose.sh $TRACKING_COMPOSE_ARGS kill && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_KAFKA/call-compose.sh $TRACKING_COMPOSE_ARGS rm -f;"

alias docker-tracking-stop-rmfv="$TRACKING_DOCKER_COMPOSE_ROOT_TR/call-compose.sh $TRACKING_COMPOSE_ARGS kill && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_TR/call-compose.sh $TRACKING_COMPOSE_ARGS rm -fv && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_TDS/call-compose.sh $TRACKING_COMPOSE_ARGS kill && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_TDS/call-compose.sh $TRACKING_COMPOSE_ARGS rm -fv && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_KAFKA/call-compose.sh $TRACKING_COMPOSE_ARGS kill && \
                            $TRACKING_DOCKER_COMPOSE_ROOT_KAFKA/call-compose.sh $TRACKING_COMPOSE_ARGS rm -fv;"

alias docker-tracking-logs="$TRACKING_DOCKER_COMPOSE_ROOT_TR/call-compose.sh $TRACKING_COMPOSE_ARGS logs"
alias docker-tds-logs="$TRACKING_DOCKER_COMPOSE_ROOT_TDS/call-compose.sh $TRACKING_COMPOSE_ARGS logs"
alias docker-kafka-logs="$TRACKING_DOCKER_COMPOSE_ROOT_KAFKA/call-compose.sh $TRACKING_COMPOSE_ARGS logs"


#RLR
alias docker-rlr-start-integration="$RLR_ROOT/build/start-db-env.sh"
alias docker-rlr-start="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh $RLR_COMPOSE_ARGS up -d"
alias docker-rlr-stop="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh $RLR_COMPOSE_ARGS kill && \
                       $RLR_DOCKER_COMPOSE_ROOT/call-compose.sh $RLR_COMPOSE_ARGS rm -f"
alias docker-rlr-stop-rmfv="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh $RLR_COMPOSE_ARGS kill && \
                       $RLR_DOCKER_COMPOSE_ROOT/call-compose.sh $RLR_COMPOSE_ARGS rm -fv"
alias docker-rlr-logs="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh $RLR_COMPOSE_ARGS logs"

#docker test
#TODO add instance-name parameters
#TODO add since parameter (last 24 hours!)
alias docker-tracking-test-logs="$TRACKING_DOCKER_COMPOSE_ROOT_TR/call-compose.sh docker@emea-jas-a12t.hwl-family.net test user-acceptance-b logs --follow"
alias docker-rlr-test-logs="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh docker@emea-jas-a12t.hwl-family.net test rlr-test logs --follow"

#other aliases
alias setup-ssh-tunnel-a12t="ssh -L 8777:localhost:33609 docker@emea-jas-a12t.hwl-family.net"
alias start-notes="$HOME/scripts/hellmann/start-notes.sh"
alias diff-develop-integration="git log --graph --pretty=format:'%Cred%h%Creset %s %Cgreen(%cr)%Creset' --abbrev-commit --date=relative --first-parent origin/develop..origin/integration"
alias vpn-hellmann="sudo openvpn --client --config ~/openvpn-hellmann/client-mathias.ovpn"
alias keepass-hellmann="/usr/lib/keepass2/KeePass.exe /home/snemeth/Dropbox/work/hellmann/keepass/keepass-own.kdbx"
alias copy-chat-history="docker cp notes:/home/notes/Documents/SametimeTranscripts/ $HOME/notes-chat-history"
alias edit-hellmann-aliases="vi $LINUX_ENV_REPO/workplace-specific/hellmann/aliases/aliases.sh"
