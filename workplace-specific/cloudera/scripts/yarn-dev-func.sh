#!/usr/bin/env bash

function setup() {
    export UPSTREAM_HADOOP_DIR=$HADOOP_DEV_DIR
    export DOWNSTREAM_HADOOP_DIR=$CLOUDERA_HADOOP_ROOT
}

##TODO add force mode: ignore whitespace issues and make backup of patch!
function yarn-save-patch() {
    setup
    BRANCH_NAME=$(git rev-parse --symbolic-full-name --abbrev-ref HEAD)
    if [ "$BRANCH_NAME" = "trunk" ]; then
        echo "Cannot make patch, current branch is trunk!"
        return 1
    fi
    
    if [ "$BRANCH_NAME" = "" ]; then
        echo "You are probably not in a git repository!"
        return 2
    fi
    
    PATCH_BASEDIR="$HOME/yarn-tasks/"
    
    #TODO check if git is clean (no modified, unstaged files, etc)
    #pull trunk, rebase current branch to trunk
    set -e
    git checkout trunk && git pull && git checkout - && git rebase trunk
    set +e
    
    git diff trunk --check
    if [ $? -ne 0 ]; then
        echo "There are trailing whitespaces in the diff, please fix them!"
        return 3
    fi
    
    #make directory in yarn-tasks if not yet exists
    if [ ! -d "$BRANCH_NAME" ]; then
        mkdir -p $PATCH_BASEDIR/$BRANCH_NAME
    fi
    
    #find latest patch number from existing patches
    #TODO use -name option of find
    find $PATCH_BASEDIR/$BRANCH_NAME -type f -print | grep "$BRANCH_NAME\.\d*.patch\$"
    
    #TODO this one also works: bla=$((001 + 1))
    if [ $? -ne 0 ]; then
        PATCH_NO_STR="001"
    else
        LAST_PATCH_STR=$(basename $(find $PATCH_BASEDIR/$BRANCH_NAME -type f -print | grep "$BRANCH_NAME\.\d*.patch\$" | sort -r | head -n 1) | cut -d '.' -f 2)
        #remove leading zeros
        LAST_PATCH_NO=$(echo $LAST_PATCH_STR | sed 's/^0*//')
        PATCH_NO_STR=$(seq -f '%03g' $LAST_PATCH_NO $(($LAST_PATCH_NO + 1)) | tail -n 1)
    fi
    
    PATCH_FILE="$PATCH_BASEDIR/$BRANCH_NAME/$BRANCH_NAME.$PATCH_NO_STR.patch"
    git diff trunk > $PATCH_FILE
    #TODO replacing all spaces in patch file caused issues when patch applied
    #sed -i 's/^\([+-].*\)[ \t]*$/\1/' $PATCH_FILE
    PATCH_FILE_DU_RESULT=$(du -h $PATCH_FILE)
    echo "Created patch file: $PATCH_FILE_DU_RESULT"
    
    ##Sanity check: try to apply patch
    git checkout trunk
    git apply $PATCH_FILE --check
    git checkout -
    if [ $? -ne 0 ]; then
        echo "ERROR: Patch does not apply to trunk!"
        return 3
    else
        echo "Patch $PATCH_FILE applies cleanly to trunk!"
    fi
    
    #"/tmp/yarndiff-$(BRANCH_NAME)-$(PATCH_NO_STR)"
}

function yarn-create-review-branch() {
    setup
    ORIG_BRANCH=$(git rev-parse --symbolic-full-name --abbrev-ref HEAD)
    PATCH_FILE=$1
    
    if [ "$PATCH_FILE" = "" ]; then
        echo "Please specify a valid patch file!"
        return 1
    fi
    if [ ! -f $PATCH_FILE ]; then
        echo "File not found: $1, Please specify a valid patch file!"
        return 2
    fi
    FILE_NAME_REGEX=".*YARN-[0-9]+.*\.patch"
    
    #try to match patch file to pattern and store branch name
    if [[ ! $PATCH_FILE =~ $FILE_NAME_REGEX ]]; then
        echo "Filename does not match usual patch file pattern: '$FILE_NAME_REGEX', exiting...!"
        return 3
    fi
    BRANCH="review-$(echo $PATCH_FILE | sed -E "s/.*(YARN-[[:digit:]]+).*/\1/g")"
    
    #pull new changes
    cd $UPSTREAM_HADOOP_DIR
    
    GIT_STATUS_OUT="$(git status --porcelain)"
    if [ ! -z "$GIT_STATUS_OUT" ]; then
        echo "git working directory is not clean, please stash or drop your changes!"
        echo "$GIT_STATUS_OUT"
        return 4 
    fi
    
    echo "Pulling latest changes from origin/trunk...."
    git checkout trunk && git pull origin
    
    #try to apply PATCH_FILE to trunk
    git apply $PATCH_FILE --check
    if [ $? -ne 0 ]; then
        echo "ERROR: Patch does not apply to trunk, please resolve the conflicts and run: git commit -am \"patch file: $PATCH_FILE\""
        git checkout $ORIG_BRANCH
        return 3
    else
        echo "Patch $PATCH_FILE applies cleanly to trunk, checking out new branch $BRANCH from trunk!"
        if [ `git branch --list "$BRANCH"` ]; then
            git checkout "$BRANCH"
        else
            git checkout -b "$BRANCH" trunk
        fi
        git apply $PATCH_FILE
        git commit -am "patch file: $PATCH_FILE"
    fi
}

#TODO decide on the cdh branch whether this is C5 or C6 backport (remote is different)
function yarn-backport-c6() {
    setup
    if [[ $# -ne 3 ]]; then
        echo "Usage: yarn-backport-c6 [CDH-jira-number] [CDH-branch] [Upstream commit hash or commit message fragment]"
        echo "Example: yarn-backport-c6 CDH-64201 cdh6.x YARN-7948"
        return 1
    fi
    CDH_JIRA_NO=$1
    CDH_BRANCH=$2
    UPSTREAM_PATCH_NO=$3
    
    ##fetch, pull, store commit hash of upstream commit
    cd $UPSTREAM_HADOOP_DIR
    ORIG_BRANCH=$(git rev-parse --symbolic-full-name --abbrev-ref HEAD)
    git fetch --all && git checkout trunk && git pull
    
    IFS=$'\n'
    GIT_LOG_RES=($(git log --oneline --grep=${UPSTREAM_PATCH_NO}))
    unset IFS
    echo "git log res: ${GIT_LOG_RES[@]}"
    if [[ ${#GIT_LOG_RES[@]} -ne 1 ]]; then 
        echo "Multiple results found in git log of upstream repository for pattern: $UPSTREAM_PATCH_NO";
        #restore original upstream branch
        git checkout ${ORIG_BRANCH}
        return 1 
    fi
    
    UPSTREAM_COMMIT_HASH=$(echo ${GIT_LOG_RES} | cut -d' ' -f1)
    #restore original upstream branch
    git checkout ${ORIG_BRANCH}
    
    
    ###do the rest of the work in the cloudera repo
    cd $DOWNSTREAM_HADOOP_DIR
    git fetch --all 
    git checkout -b "$CDH_JIRA_NO-$CDH_BRANCH" cauldron/$CDH_BRANCH
    git cherry-pick -x $UPSTREAM_COMMIT_HASH
    
    if [ $? -ne 0 ]; then
        echo "!!!There was merge conflicts, please resolve them!!!"
        return 1
    fi
    
    #TODO check result of cherry-pick (could be non-zero if we have merge conflicts)
    ##add CDH number and it will add gerrit Change-Id
    OLD_MSG=$(git log --format=%B -n1)
    git commit --amend -m"$CDH_JIRA_NO: $OLD_MSG"
    
    
    ##run build to verify backport compiles fine
    #TODO make an option that decides if mvn clean install should be run!
    #mvn clean install -Pdist -DskipTests -Pnoshade  -Dmaven.javadoc.skip=true
    
    
    ##push to gerrit
    echo "Commit was successful! Run this command to push to gerrit: git push cauldron HEAD:refs/for/$CDH_BRANCH"
    #git push cauldron HEAD:refs/for/$CDH_BRANCH

}