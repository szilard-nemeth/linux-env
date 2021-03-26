#!/usr/bin/env bash

function sync-linux-env-repo() {
    # BASED ON THIS ANSWER: https://github.community/t5/How-to-use-Git-and-GitHub/Adding-a-folder-from-one-repo-to-another/m-p/5574#M1817
    local tmp_dir=$(mktemp -d -t kb-private-XXXXXX)
    local repo_name="linux-env"
    #local dir_to_include="cloudera"
    local original_dir=$(pwd)
    
    cd ${tmp_dir}
    echo "Using temporary dir to clone repo: $tmp_dir"
    git clone git@github.com:szilard-nemeth/linux-env.git
    cd ${repo_name}
    
    #Remove remote, just to be safe
    git remote rm origin
    
    #Filter dirs
    #git filter-branch --subdirectory-filter ${dir_to_include} -- --all
    #echo "Finished filtering project, included dir: $dir_to_include"
    
    echo "Found commits: "
    git lg
    
    #Setup committer info
#    git config user.name "Szilard Nemeth"
#    git config user.email "szilard.nemeth88@gmail.com"

    #Push to cloudera repo (mirror)
    git remote add origin git@github.infra.cloudera.com:snemeth/linux-env-mirror.git
    git push -f origin master
    
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