#!/bin/bash
#/opt/hadoop/etc/hadoop/yarn-site.xml

function sshcommand() {
  host=$1
  cmd="$2"
  echo "[Remote host: $host] Executing command: $cmd"
  set -x
  ssh systest@$host $cmd 2>/dev/null
  retcode=$?
  set +x
  return $retcode
}


function discover() {
  for host in ${CLUSTER_HOSTS[@]}; do
    sshcommand $host "ps auxww | grep java | grep NodeManager | grep -v grep"
    if [ $? -eq 0 ]; then
      NM_HOSTS+=($host)
    fi
    
    sshcommand $host "ps auxww | grep java | grep ResourceManager | grep -v grep"
    if [ $? -eq 0 ]; then
      RM_HOSTS+=($host)
    fi
  done
}

function copy-scripts-to-all-cluster-hosts() {
  for host in ${CLUSTER_HOSTS[@]}; do
    echo "Copying scripts to host: $host"
    scp ../*.sh systest@$host: 2>/dev/null
  done
}

function copy-configs-to-all-cluster-hosts() {
  for host in ${CLUSTER_HOSTS[@]}; do
    echo "Copying config files to host: $host"
    scp $tc/yarn-site.xml systest@$host:/opt/hadoop/etc/hadoop/yarn-site.xml 2>/dev/null
  done
}

function cleanup-testresults-on-all-cluster-hosts() {
  TC_RESULTS_DIR="/tmp/testcase-results/"
  for host in ${CLUSTER_HOSTS[@]}; do
    sshcommand $host "rm -rf $TC_RESULTS_DIR && mkdir -p $TC_RESULTS_DIR"
  done
}

function run-script-rm-hosts() {
  LOG_DIR="$TC_RESULT_DIR/logs"
  SCRIPT="$1"
  echo "Executing $SCRIPT on all RM machines"
  for host in ${RM_HOSTS[@]}; do
    sshcommand $host "mkdir -p $LOG_DIR && ~/$SCRIPT $tc $TC_RESULT_DIR $RM_HOST &> $LOG_DIR/$SCRIPT.log"
  done
}

function run-script-nm-hosts() {
  LOG_DIR="$TC_RESULT_DIR/logs"
  SCRIPT="$1"
  echo "Executing $SCRIPT on all NM machines"
  for host in ${NM_HOSTS[@]}; do
    sshcommand $host "mkdir -p $LOG_DIR && ~/$SCRIPT $tc $TC_RESULT_DIR $RM_HOST &> $LOG_DIR/$SCRIPT.log"
  done
}

function save-testresults-from-cluster-to-local() {
  #Results are already zipped by post-app-completed-*-remote.sh on the nodes
  local_result_dir="$LOCAL_TESTRESULTS_DIR/$tc/"
  rm -rf $local_result_dir;mkdir -p $local_result_dir
  
  for host in ${RM_HOSTS[@]}; do
    remote_tc_result_file="tc-result-$tc-$host-resourcemanager.tar.gz"
    scp systest@$host:$remote_tc_result_file $local_result_dir/$host.tar.gz
  done
  
  for host in ${NM_HOSTS[@]}; do
    remote_tc_result_file="tc-result-$tc-$host-nodemanager.tar.gz"
    scp systest@$host:$remote_tc_result_file $local_result_dir/$host.tar.gz
  done
}

function run-testcases() {
  echo "Current cluster: "
  RM_HOST=${RM_HOSTS[0]}
  echo "NM hosts: ${NM_HOSTS[@]}"
  echo "RM hosts: ${RM_HOSTS[@]}"
  echo "First RM host: $RM_HOST"

  cd testcases
  #set -x
  set -e

  #scp all scripts to cluster hosts --> Can be done once before all TCs
  copy-scripts-to-all-cluster-hosts

  #Cleanup on remote host --> Can be done once before all TCs
  cleanup-testresults-on-all-cluster-hosts
  
  local currdate=$(date +%Y%m%d_%H%M%S)
  LOCAL_TESTRESULTS_DIR="../testcase_results/$currdate"
  mkdir -p "$LOCAL_TESTRESULTS_DIR"
  rm latest && ln -s "$LOCAL_TESTRESULTS_DIR" "../testcase_results/latest"

  for tc in */ ; do
    echo "Running testcase: $tc"
    tc=$(echo $tc | tr -d '/')
    TC_RESULT_DIR="$TC_RESULTS_DIR/$tc"
    
    #scp all config files to all cluster hosts
    copy-configs-to-all-cluster-hosts

    #Setup
    run-script-rm-hosts "setup-rm-remote.sh"
    run-script-nm-hosts "setup-nm-remote.sh"
    
    echo "Sleeping for 10 seconds..." && sleep 10

    #Launch pi job
    SCRIPT="launch-mr-pi-job-remote.sh"
    LOG_DIR="$TC_RESULT_DIR/logs"
    echo "Executing $SCRIPT on remote host: $RM_HOST"
    sshcommand $RM_HOST "~/$SCRIPT | tee $LOG_DIR/$SCRIPT.log" 

    #Run post-app actions
    run-script-rm-hosts "post-app-completed-rm-remote.sh"
    run-script-nm-hosts "post-app-completed-nm-remote.sh"

    echo "Final step: Saving testcase results to local machine from all cluster hosts..."
    save-testresults-from-cluster-to-local
  done
  
  set +x
  set +e
}

#set -x
RM_PORT=8088
NM_PORT=8042
CLUSTER_HOSTS=(ccycloud-1.snemeth-netty2.root.hwx.site ccycloud-2.snemeth-netty2.root.hwx.site ccycloud-3.snemeth-netty2.root.hwx.site)
NM_HOSTS=()
RM_HOSTS=()
discover
run-testcases
