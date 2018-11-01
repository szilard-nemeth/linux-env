#!/usr/bin/env bash

##TODO add force mode: ignore whitespace issues and make backup of patch!
function save-patch() {
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
    git co trunk && git pull && git co - && git rebase trunk
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
    git co trunk
    git apply $PATCH_FILE --check
    git co -
    if [ $? -ne 0 ]; then
        echo "ERROR: Patch does not apply to trunk!"
        return 3
    else
        echo "Patch $PATCH_FILE applies cleanly to trunk!"
    fi
    
    #"/tmp/yarndiff-$(BRANCH_NAME)-$(PATCH_NO_STR)"
}
