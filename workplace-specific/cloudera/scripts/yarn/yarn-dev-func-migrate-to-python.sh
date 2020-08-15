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