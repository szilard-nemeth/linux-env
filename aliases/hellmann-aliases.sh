#setup locations
HELLMANN_DEV_ROOT="$HOME/development/hellmann-repos/"
TRACKING_ROOT="$HELLMANN_DEV_ROOT/trackingall/"
TRACKING_DOCKER_COMPOSE_ROOT="$TRACKING_ROOT/tracking-docker/tracking-docker-compose/tracking/"
RLR_ROOT="$HELLMANN_DEV_ROOT/rlr/"
RLR_DOCKER_COMPOSE_ROOT="$RLR_ROOT/rlr-docker-compose/rlr/"



#alias functions
mavenSetVersion() {
	mvn versions:set -DnewVersion=$1
}

alias mount-allshare="sudo mount.cifs //172.24.227.38/ALLSHARE /mnt/allshare/ -o user=snemeth"

#goto aliases
alias goto-tracking="cd $HELLMANN_DEV_ROOT/trackingall"
alias goto-rlr="cd $HELLMANN_DEV_ROOT/rlr"

#maven aliases
alias mvn-ci="mvn clean install"
alias mvn-ci-skiptest="mvn clean install -DskipTests"
alias mvn-ci-skip-all="mvn clean install -DskipTests -Dnogwt -Dnodocker"
alias mvn-setversion=mavenSetVersion

#docker aliases
#Tracking
alias docker-tracking-start-int-env="$TRACKING_ROOT/build/start-integration-env.sh"
alias docker-tracking-start-env="$TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local tracking_1 up"
alias docker-tracking-stop-env="$TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local tracking_1 kill && $TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local tracking_1 rm -fv"
alias docker-tracking-logs="$TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local tracking_1 logs"
#RLR
alias docker-rlr-start-int-env="$RLR_ROOT/build/start-db-env.sh"
alias docker-rlr-start-env="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local rlr_1 up"
alias docker-rlr-stop-env="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local rlr_1 kill && $RLR_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local rlr_1 rm -fv"
alias docker-rlr-logs="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh localhost local rlr_1 logs"

#docker test
#TODO add instance-name parameters
#TODO add since parameter (last 24 hours!)
alias docker-tracking-test-logs="$TRACKING_DOCKER_COMPOSE_ROOT/call-compose.sh docker@emea-jas-a12t.hwl-family.net test user-acceptance-b logs --follow"
alias docker-rlr-test-logs="$RLR_DOCKER_COMPOSE_ROOT/call-compose.sh docker@emea-jas-a12t.hwl-family.net test rlr-test logs --follow"

#other aliases
alias setup-ssh-tunnel-a12t="ssh -L 8777:localhost:33609 docker@emea-jas-a12t.hwl-family.net"
alias start-notes="$HOME/scripts/hellmann/start-notes.sh"
alias develop-integration-diff="git log --graph --pretty=format:'%Cred%h%Creset %s %Cgreen(%cr)%Creset' --abbrev-commit --date=relative --first-parent origin/develop..origin/integration"
alias vpn-hellmann="sudo openvpn --client --config ~/openvpn-hellmann/client-mathias.ovpn"
