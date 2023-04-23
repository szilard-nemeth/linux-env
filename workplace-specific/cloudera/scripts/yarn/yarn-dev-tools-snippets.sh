#!/usr/bin/env bash

function setup() {
    export UPSTREAM_HADOOP_DIR=${HADOOP_DEV_DIR}
    export DOWNSTREAM_HADOOP_DIR=${CLOUDERA_HADOOP_ROOT}
    export TASKS_DIR="$HOME/yarn-tasks/"
}

#####LESS COMPLEX SCRIPTS CAN STAY HERE, AS IT'S NOT WORTH IT TO MIGRATE THESE SMALL SCRIPTS TO PYTHON
function yarn-get-remote-cm-nm-dir() {
    #Example usage: get-remote-cm-nm-dir bsteinbach-gpu-2.vpc.cloudera.com
    local host="$1"
    local process_dir="/var/run/cloudera-scm-agent/process/"
    local get_nm_dir_cmd='nm_dir=$(sudo ls -t /var/run/cloudera-scm-agent/process/| grep -m 1 yarn-NODEMANAGER);'"echo $process_dir/"'$nm_dir'
    ssh "systest@${host}" "set -x;$get_nm_dir_cmd;sudo ls -latr $process_dir/"'$nm_dir'
}

function yarn-get-remote-cm-nm-dir-public-cloud() {
    #Example usage: get-remote-cm-nm-dir bsteinbach-gpu-2.vpc.cloudera.com
    local host="$1"
    local process_dir="/var/run/cloudera-scm-agent/process/"
    local get_nm_dir_cmd='nm_dir=$(sudo ls -t /var/run/cloudera-scm-agent/process/| grep -m 1 yarn-NODEMANAGER);'"echo $process_dir/"'$nm_dir'
    ssh -i ~/.ssh/hw-priv-pem-key "cloudbreak@${host}" "set -x;$get_nm_dir_cmd;sudo ls -latr $process_dir/"'$nm_dir'
}

function yarn-get-remote-cm-rm-dir-public-cloud() {
    #Example usage: get-remote-cm-nm-dir bsteinbach-gpu-2.vpc.cloudera.com
    local host="$1"
    local process_dir="/var/run/cloudera-scm-agent/process/"
    local get_rm_dir_cmd='rm_dir=$(sudo ls -t /var/run/cloudera-scm-agent/process/| grep -m 1 yarn-RESOURCEMANAGER);'"echo $process_dir/"'$rm_dir'
    ssh -i ~/.ssh/hw-priv-pem-key "cloudbreak@${host}" "set -x;$get_rm_dir_cmd;sudo ls -latr $process_dir/"'$rm_dir'
}

function yarn-fetch-rm-config-from-host-public-cloud {
    local host="$1"
    local conf_file="$2"
    local process_dir="/var/run/cloudera-scm-agent/process/"
    local get_rm_dir_cmd='rm_dir=$(sudo ls -t /var/run/cloudera-scm-agent/process/| grep -m 1 yarn-RESOURCEMANAGER);'"echo $process_dir/"'$rm_dir'
    #ssh -i ~/.ssh/hw-priv-pem-key "cloudbreak@${host}" "set -x;$get_rm_dir_cmd;sudo cp $process_dir/"'$rm_dir'"/{nodes_allow.txt,nodes_exclude.txt} ~/"
    ssh -i ~/.ssh/hw-priv-pem-key "cloudbreak@${host}" "set -x;$get_rm_dir_cmd;sudo cp $process_dir/"'$rm_dir'"/$conf_file ~/;sudo chown cloudbreak ~/$conf_file"
    set -x
    echo $host
    scp -i ~/.ssh/hw-priv-pem-key cloudbreak@${host}:$conf_file "./${host}_${conf_file}"
    set +x
}


function timezones() {
    echo -n "Local time: " && TZ=CET date; \
    echo -n "Time in PA: " && TZ=America/Los_Angeles date; \
    echo -n "Time in Melbourne: " && TZ=Australia/Melbourne date; \
    echo -n "Time in Bangalore: " && TZ="UTC-5" date
}

# TODO outdated path, should use YARN dev tools
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

function yarn-downstream-version-pc-for-upstream-change {
    goto-cldr-hadoop
    res=$(git log --oneline --grep=$1)
    count=$(echo "$res" | wc -l | tr -s ' ')
    
    if [[ "$count" -ne 1 ]]; then
        echo "ERROR! Found zero or multiple lines for $1. Result: $res"
        return 1
    fi

    c_hash=$(git log -3 --pretty=format:"%h" --grep=$1)
    echo "Found commit hash: $c_hash"
    git show $c_hash:pom.xml | grep version | head -n5
}