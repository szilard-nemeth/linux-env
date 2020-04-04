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
export TARGETROOT=
export MVN_NO_DOCKER=1