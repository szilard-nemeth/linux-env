#!/usr/bin/env bash
# TODO Now we have 3 copies of the same script --> MIGRATE TO PYTHON
function sync-yarn-dev-tools-repo() {
    local tmp_dir=$(mktemp -d -t kb-private-XXXXXX)
    local repo_name="yarn-dev-tools"
    local original_dir=$(pwd)
    
    cd ${tmp_dir}
    echo "Using temporary dir to clone repo: $tmp_dir"
    git clone https://github.com/szilard-nemeth/yarn-dev-tools.git
    cd ${repo_name}
    
    #Remove remote, just to be safe
    #git remote rm origin
    
    #Push to cloudera repo (mirror)
    git remote add mirror https://github.infra.cloudera.com/snemeth/yarn-dev-tools-mirror.git
    git push -f mirror master --tags
    #git push mirror 'refs/remotes/origin/*:refs/heads/*'
    
    #Cleanup
    read -p "OK to remove directory: $tmp_dir ?" -n 1 -r
    echo    # (optional) move to a new line
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo "Removing directory: $tmp_dir"
        rm -rf ${tmp_dir}
    fi
    
    cd ${original_dir}
}