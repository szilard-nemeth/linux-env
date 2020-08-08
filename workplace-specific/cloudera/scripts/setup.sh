#!/usr/bin/env bash

export PATH="/usr/local/opt/protobuf@2.5/bin:$PATH"

## Setup Google Cloud SDK
# The next line updates PATH for the Google Cloud SDK.
if [[ -f '/Users/szilardnemeth/google-cloud-sdk/path.bash.inc' ]]; then 
    . '$HOME/google-cloud-sdk/path.bash.inc'; 
fi

# The next line enables shell command completion for gcloud.
if [[ -f '/Users/szilardnemeth/google-cloud-sdk/completion.bash.inc' ]]; then 
    . '$HOME/google-cloud-sdk/completion.bash.inc'; 
fi

#CM build specific settings
export MAVEN_OPTS='-Xmx5000m'
export TARGETROOT=
export MVN_NO_DOCKER=1

#eYARN setup / K8S setup
export K8S_NAMESPACE="snemeth-eyarn4"

echo "Setting k8s namespace to ${K8S_NAMESPACE}"
kubectl config set-context --current --namespace=${K8S_NAMESPACE}


#Setup PATH
PATH=$PATH:$HOME/development/other-repos/util-scripts
PATH=$PATH:$HOME/development/cloudera/dist_test/bin

if is-platform-macos
then
    PATH=$PATH:$HOME/Library/Python/2.7/bin
    PATH=$PATH:/Applications/CMake.app/Contents/bin
fi

#Setup GOPATH
GOPATH=/Users/szilardnemeth/go