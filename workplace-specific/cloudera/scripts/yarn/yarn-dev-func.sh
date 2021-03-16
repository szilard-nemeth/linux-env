#!/usr/bin/env bash

function setup() {
    export UPSTREAM_HADOOP_DIR=${HADOOP_DEV_DIR}
    export DOWNSTREAM_HADOOP_DIR=${CLOUDERA_HADOOP_ROOT}
    export TASKS_DIR="$HOME/yarn-tasks/"
}

#####LESS COMPLEX SCRIPTS CAN STAY HERE, AS IT'S NOT WORTH IT TO MIGRATE THESE SMALL SCRIPTS TO PYTHON
function get-remote-cm-nm-dir() {
    #Example usage: get-remote-cm-nm-dir bsteinbach-gpu-2.vpc.cloudera.com
    local host="$1"
    local process_dir="/var/run/cloudera-scm-agent/process/"
    local get_nm_dir_cmd='nm_dir=$(sudo ls -t /var/run/cloudera-scm-agent/process/| grep -m 1 yarn-NODEMANAGER);'"echo $process_dir/"'$nm_dir'
    ssh "systest@${host}" "set -x;$get_nm_dir_cmd;sudo ls -latr $process_dir/"'$nm_dir'
}

function timezones() {
    echo -n "Local time: " && TZ=CET date; \
    echo -n "Time in PA: " && TZ=America/Los_Angeles date; \
    echo -n "Time in Melbourne: " && TZ=Australia/Melbourne date; \
    echo -n "Time in Bangalore: " && TZ="UTC-5" date
}

function reviewsync() {
    python $HOME/development/my-repos/hadoop-reviewsync/reviewsync/reviewsync.py \
    --gsheet \
    --gsheet-client-secret "/Users/snemeth/.secret/client_secret_hadoopreviewsync.json" \
    --gsheet-spreadsheet "YARN/MR Reviews" \
    --gsheet-worksheet "Incoming" \
    --gsheet-jira-column "JIRA" \
    --gsheet-update-date-column "Last Updated" \
    --gsheet-status-info-column "Reviewsync" \
    -b branch-3.2 branch-3.1 -v
}

function build-upload-yarn-to-cluster() {
    setup
    if [[ $# -ne 1 ]]; then
        echo "Usage: build-upload-yarn-to-cluster [hostname]"
        echo "Example: build-upload-yarn-to-cluster <host>"
        return 1
    fi

    HOST_TO_UPLOAD=$1
    cd ${UPSTREAM_HADOOP_DIR}
    MVN_VER=$(echo '${project.version}' | mvn help:evaluate 2> /dev/null | grep -v '^[[]')
    mvn clean package -Pdist -DskipTests -Dmaven.javadoc.skip=true && scp hadoop-dist/target/hadoop-${MVN_VER}.tar.gz systest@${HOST_TO_UPLOAD}:~
}

function yarn-downstream-commits() {
    goto-cldr-hadoop
    echo "Branch: cdpd-master, author=snemeth"
    git log cdpd-master --author=snemeth --oneline

    echo "Branch: cdpd-master, committer=snemeth"
    git log cdpd-master --committer=snemeth --oneline
    cd -
}

function yarn-listupstreamversions() {
    # This will be more robust but requires switching branches:
    # https://stackoverflow.com/questions/3545292/how-to-get-maven-project-version-to-the-bash-command-line
    for branch in trunk branch-3.3 branch-3.2 branch-3.1
    do
        echo "Version on branch: $branch"
        git show ${branch}:pom.xml | grep version | head -n5
        printf "\n"
    done
}

#####ALIASES

#TODO PYTHONPATH DID NOT WORK
#TODO extract export statement and script name to variable
alias yarn-save-patch="export HADOOP_DEV_DIR; export CLOUDERA_HADOOP_ROOT; python3 $CLOUDERA_DIR/scripts/yarn/python/yarndevfunc/yarn_dev_func.py save_patch"

#Example call: yarn-create-review-branch /Users/snemeth/yarn-tasks/YARN-10277-test2/YARN-10277-test2.010.patch
alias yarn-create-review-branch="export HADOOP_DEV_DIR; export CLOUDERA_HADOOP_ROOT; python3 $CLOUDERA_DIR/scripts/yarn/python/yarndevfunc/yarn_dev_func.py create_review_branch"

#Generic call: yarn-backport-c6 [Upstream commit hash or commit message fragment] [CDH-jira-number] [CDH-branch]
#Example call: yarn-backport-c6 YARN-7948 CDH-64201 CDH-64201-cdh6x
alias yarn-backport-c6="export HADOOP_DEV_DIR; export CLOUDERA_HADOOP_ROOT; python3 $CLOUDERA_DIR/scripts/yarn/python/yarndevfunc/yarn_dev_func.py backport_c6"

#Generic call: yarn-upstream-commit-pr [github-username] [remote-branch]
#Example call: yarn-upstream-commit-pr szilard-nemeth YARN-9999
alias yarn-upstream-commit-pr="export HADOOP_DEV_DIR; export CLOUDERA_HADOOP_ROOT; python3 $CLOUDERA_DIR/scripts/yarn/python/yarndevfunc/yarn_dev_func.py upstream_pr_fetch"

#Generic call: yarn-diff-patches [JIRA_ID] [branches]
#Example call: yarn-diff-patches YARN-7913 trunk branch-3.2 branch-3.1
alias yarn-diff-patches="export HADOOP_DEV_DIR; export CLOUDERA_HADOOP_ROOT; python3 $CLOUDERA_DIR/scripts/yarn/python/yarndevfunc/yarn_dev_func.py diff_patches_of_jira"

#Generic call: save-diff-as-patches [refspec-to-diff-head-with] [destination-directory-prefix]"
#Example call: save-diff-as-patches master gpu
#Example call: save-diff-as-patches master WIP-migrate-yarn-scripts-to-python ~/yarn-tasks/saved_patches prefix1
alias save-diff-as-patches="export HADOOP_DEV_DIR; export CLOUDERA_HADOOP_ROOT; python3 $CLOUDERA_DIR/scripts/yarn/python/yarndevfunc/yarn_dev_func.py save_diff_as_patches"

#Example call: yarn-get-umbrella-data YARN-5734
alias yarn-get-umbrella-data="export HADOOP_DEV_DIR; export CLOUDERA_HADOOP_ROOT; python3 $CLOUDERA_DIR/scripts/yarn/python/yarndevfunc/yarn_dev_func.py fetch_jira_umbrella_data"