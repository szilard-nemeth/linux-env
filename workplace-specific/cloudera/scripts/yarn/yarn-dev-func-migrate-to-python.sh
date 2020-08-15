function yarn-upstream-commit-pr() {
    if [[ $# -ne 2 ]]; then
        echo "Usage: yarn-upstream-commit-pr [github-username] [remote-branch]"
        echo "Example: yarn-upstream-commit-pr szilard-nemeth YARN-9999"
        echo "Example 2: yarn-upstream-commit-pr pingsutw YARN-9989"
        return 1
    fi
    GITHUB_USER=$1
    REMOTE_BRANCH=$2

    git fetch https://github.com/${GITHUB_USER}/hadoop.git ${REMOTE_BRANCH}
    if [[ $? -ne 0 ]]; then
        echo "Cannot fetch from remote branch: $GITHUB_USER/$REMOTE_BRANCH"
        return 1
    fi


    echo "Printing 10 topmost commits of FETCH_HEAD"
    git lg FETCH_HEAD | head -n 10

    echo "Printing diff of trunk..FETCH_HEAD..."
    git log trunk..FETCH_HEAD  --oneline
    num_commits=$(git log trunk..FETCH_HEAD  --oneline  | wc -l | tr -s ' ')

    if [[ ${num_commits} -ne 1 ]]; then
        echo "Number of commits between trunk..FETCH_HEAD is not 1! Exiting..."
        return 2
    fi

    git cherry-pick FETCH_HEAD
    echo "REMEMBER to change the commit message with command: 'git commit --amend'"
    echo "REMEMBER to reset the author with command: 'git commit --amend --reset-author"
}

function save-patches() {
    setup

    if [[ -z "$TASKS_DIR" ]]; then
        echo "You need to specify the variable 'TASKS_DIR' first (preferably in function called 'setup')"
        return 3
    fi

    if [[ $# -ne 2 ]]; then
        echo "Usage: save-patches [refspec-to-diff-head-with] [destination-directory-prefix]"
        echo "Example: save-patches master gpu"
        return 1
    fi

    GIT_BASE_BRANCH="$1"
    DIR_PREFIX="$2"

    git rev-parse --verify ${GIT_BASE_BRANCH}

    if [[ $? -ne 0 ]]; then
        echo "Specified branch is not valid: $GIT_BASE_BRANCH"
        return 1
    fi

    GIT_HEAD=$(git rev-parse --symbolic-full-name --abbrev-ref HEAD)
    if [[ "$GIT_HEAD" = "" ]]; then
        echo "You are probably not in a git repository!"
        return 2
    fi


    DEST_BASEDIR="$TASKS_DIR/$DIR_PREFIX/$(date +%Y%m%d_%H%M%S)"

    #TODO check if git is clean (no modified, unstaged files, etc)
    #pull trunk, rebase current branch to trunk
    git checkout ${GIT_BASE_BRANCH} && git pull || { echo "Pull failed!"; exit 1; }
    git checkout - && git rebase ${GIT_BASE_BRANCH} || { echo "Rebase failed and it was aborted! Please rebase manually!"; git rebase --abort; return 1; }

    #TODO put this back in
#    git diff ${GIT_BASE_BRANCH} --check
#    if [[ $? -ne 0 ]]; then
#        echo "There are trailing whitespaces in the diff, please fix them!"
#        return 4
#    fi

    GIT_FORMAT_PATCH_OUTPUT_DIR="$(mktemp -d -t gpu)"
    git format-patch ${GIT_BASE_BRANCH} --output-directory ${GIT_FORMAT_PATCH_OUTPUT_DIR} --full-index

    #make sure destination directory exists
    if [[ ! -d "$DEST_BASEDIR" ]]; then
        mkdir -p ${DEST_BASEDIR}
    fi

    echo "Saving git patches from ${GIT_FORMAT_PATCH_OUTPUT_DIR} to $DEST_BASEDIR/"
    mv ${GIT_FORMAT_PATCH_OUTPUT_DIR}/* ${DEST_BASEDIR}/

    #remove temp dir
    rmdir ${GIT_FORMAT_PATCH_OUTPUT_DIR}
}

function get-umbrella-data() {
    jira="$1"
    base_dir="/tmp/jira-umbrella-data/"
    dir="$base_dir/$jira"
    mkdir -p ${dir}

    jira_html_file="$dir/jira.html"
    jira_list_file="$dir/jira-list.txt"
    commits_file="$dir/commit-hashes.txt"
    changed_files_file="$dir/changed-files.txt"
    summary_file="$dir/summary.txt"

    echo -n "" > ${summary_file}

    curl https://issues.apache.org/jira/browse/${jira} > ${jira_html_file}

    grep "a class=\"issue-link\"" ${jira_html_file} | grep -v "$jira" | egrep -o "data-issue-key=\".*\"" | sed -E 's/^.*key="(.*)" .*/\1/p' | uniq > ${jira_list_file}
    jira_list=$(printf "%s|\0" $(<${jira_list_file}))

    #Delete last character
    #https://unix.stackexchange.com/questions/144298/delete-the-last-character-of-a-string-using-string-manipulation-in-shell-script/144345
    jira_list=$(echo "${jira_list%?}")
#    echo "Jira list: ${jira_list}"

    pushd ${HADOOP_DEV_DIR} 2>&1 > /dev/null
    BRANCH_NAME=$(git rev-parse --symbolic-full-name --abbrev-ref HEAD)
    if [[ "$BRANCH_NAME" != "trunk" ]]; then
        echo "Current branch is not trunk!"
        popd 2>&1 > /dev/null
        return 1
    fi

    #Get commits in reverse order (oldest first)
    git log --oneline | egrep ${jira_list} | cut -d ' ' -f1 | tail -r > ${commits_file}
    git log --oneline | egrep ${jira_list} | cut -d ' ' -f1 | xargs -n 1 git diff-tree --no-commit-id --name-only -r | sort -u > ${changed_files_file}

    #Write summary file
    echo "Number of jiras: $(cat ${jira_list_file} | wc -l | awk '{print $1}')" >> ${summary_file}
    echo "Number of commits: $(cat ${commits_file} | wc -l | awk '{print $1}')" >> ${summary_file}
    echo "Number of files changed: $(cat ${changed_files_file} | wc -l | awk '{print $1}')" >> ${summary_file}

    #Iterate over commit hashes file, print the following to summary_file for each commit hash:
    # <hash> <YARN-id> <commit date>
    while IFS= read -r hash; do
        commit_msg=$(git show --no-patch --no-notes --oneline ${hash})
        yarn_id=$(echo ${commit_msg} | cut -d' ' -f2)
        commit_date=$(git show --no-patch --no-notes --pretty='%cI' ${hash})
        echo "$commit_msg $commit_date" >> ${summary_file}
    done < ${commits_file}

    #Iterate over changed files, print all matching changes to the particular file
    #Create changes file for every touched file
    while IFS= read -r changed_file; do
        target_file="${dir}/changes-"$(basename ${changed_file})
        git log --follow --oneline -- ${changed_file} | egrep ${jira_list} > ${target_file}
    done < ${changed_files_file}

    echo "Summary: "
    cat ${summary_file}

    echo "All result files: "
    find ${dir}
    popd 2>&1 > /dev/null
}

function yarn-diff-patches() {
    #example:
    #1. git lg trunk | grep 10028
    #* 13cea0412c1 - YARN-10028. Integrate the new abstract log servlet to the JobHistory server. Contributed by Adam Antal (24 hours ago) <Szilard Nemeth>
    #
    #2. git diff 13cea0412c1..13cea0412c1^ > /tmp/YARN-10028-trunk.diff
    #3. git co branch-3.2
    #4. git apply ~/Downloads/YARN-10028.branch-3.2.001.patch
    #5. git diff > /tmp/YARN-10028-branch-32.diff
    #6. diff -Bibw /tmp/YARN-10028-trunk.diff /tmp/YARN-10028-branch-32.diff


    ###THIS SCRIPT ASSUMES EACH PROVIDED BRANCH WITH PARAMETERS (e.g. trunk, 3.2, 3.1) has the given commit committed
    if [[ $# -ne 2 ]]; then
        echo "Usage: diff-patches [JIRA_ID] [branches]"
        echo "Example: YARN-7913 trunk,branch-3.2,branch-3.1"
        return 1
    fi
    mkdir -p /tmp/yarndiffer

    YARN_ID=$1
    IFS=', ' read -r -a branches <<< "$2"

    #Validate branches, generate diffs
    for br in "${branches[@]}"; do
        git rev-parse --verify ${br}

        if [[ $? -ne 0 ]]; then
            echo "Specified branch is not valid: $br"
            return 1
        fi
        no_of_commits=$(git log ${br} --oneline | grep ${YARN_ID} | wc -l | tr -s ' ')


        if [[ ${no_of_commits} -eq 0 ]]; then
            echo "Specified branch $br does not contain commit for $YARN_ID"
            return 1
        elif [[ ${no_of_commits} -ne 1 ]]; then
            echo "Specified branch $br has multiple commits for $YARN_ID"
            return 1
        fi

        hash=$(git log ${br} --oneline | grep ${YARN_ID} | cut -d ' ' -f1)

        git diff ${hash}^..${hash} > /tmp/yarndiffer/${YARN_ID}-${br}.diff
    done
    echo "Generated diffs: "
    du -sh /tmp/yarndiffer/${YARN_ID}-*
}