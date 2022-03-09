#!/usr/bin/env bash
##SKIPSOURCING##

EYARN_DIR="$CLOUDERA_DEV_ROOT/yarn-operator"

## Setup Google Cloud SDK
# The next line updates PATH for the Google Cloud SDK.
if [[ -f '/Users/snemeth/google-cloud-sdk/path.bash.inc' ]]; then 
    . '$HOME/google-cloud-sdk/path.bash.inc'; 
fi

# The next line enables shell command completion for gcloud.
if [[ -f '/Users/snemeth/google-cloud-sdk/completion.bash.inc' ]]; then 
    . '$HOME/google-cloud-sdk/completion.bash.inc'; 
fi


#eYARN setup / K8S setup
export K8S_NAMESPACE="snemeth-eyarn4"
#echo "Setting k8s namespace to ${K8S_NAMESPACE}"
#kubectl config set-context --current --namespace=${K8S_NAMESPACE}

#Setup GOPATH
GOPATH=/Users/snemeth/go