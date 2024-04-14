#!/usr/bin/env bash

function sync-kb-private-repo {
    # BASED ON THIS ANSWER: https://github.community/t5/How-to-use-Git-and-GitHub/Adding-a-folder-from-one-repo-to-another/m-p/5574#M1817
    local tmp_dir=$(mktemp -d -t kb-private-XXXXXX)
    local repo_name="knowledge-base-private"
    local dir_to_include="cloudera"
    local original_dir=$(pwd)
    
    cd ${tmp_dir}
    echo "Using temporary dir to clone repo: $tmp_dir"
    git clone git@github.com:szilard-nemeth/knowledge-base-private.git
    cd ${repo_name}
    
    #Remove remote, just to be safe
    git remote rm origin
    
    #Filter dirs
    git filter-branch --subdirectory-filter ${dir_to_include} -- --all
    echo "Finished filtering project, included dir: $dir_to_include"
    
    echo "Found commits: "
    git lg
    
    #Setup committer info
    git config user.name "Szilard Nemeth"
    git config user.email "szilard.nemeth88@gmail.com"
    
    ####COMMENT THIS OUT IF ORIGINAL DIR STRUCTURE MUST BE PRESERVED!
#    #Moves files back in their original place and commit
#    local fmt_date=$(date +%Y%m%d_%H:M:S)
#    mkdir ${dir_to_include}
#    mv * ${dir_to_include}
#    git add .
#    git commit -m "Filter branch commit based on dir: ${dir_to_include} at: $fmt_date"

    ####COMMENT THIS OUT IF TRADITIONAL PULL IS REQUIRED TO ANOTHER REPO
    #Pull changes into cloudera repo
#    local kb_repo_cloudera="$CLOUDERA_DEV_ROOT/knowledge-base"
#    cd ${kb_repo_cloudera}
#    git checkout master
#    git remote add modified-source "${tmp_dir}/${repo_name}"
#    git pull modified-source master --allow-unrelated-histories
#    git remote rm modified-source
#    echo "Pulled changes into $kb_repo_cloudera"

    #Push to cloudera repo (mirror)
    git remote add origin git@github.infra.cloudera.com:snemeth/knowledge-base-mirror.git
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