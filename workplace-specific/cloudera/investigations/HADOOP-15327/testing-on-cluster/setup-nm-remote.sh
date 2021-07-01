#!/bin/bash

function turn-on-shufflehandler-debug-logs() {
  # Turn on debug logging for ShuffleHandler
  for host in ${NM_HOSTS[@]}; do
    sshcommand $host "/opt/hadoop/bin/yarn daemonlog -setlevel `hostname`:$NM_PORT org.apache.hadoop.mapred.ShuffleHandler.java DEBUG"
  done
}

set -x
tc=$1
TC_RESULT_DIR="$2"
rmhost=$3

#Fix RM hostname in yarn-site.xml
sudo sed -i -e 's/master.cloudera.com/'$rmhost'/g' /opt/hadoop/etc/hadoop/yarn-site.xml
cp /opt/hadoop/etc/hadoop/yarn-site.xml $TC_RESULT_DIR/yarn-site.xml


#Restart NM
/opt/hadoop/bin/yarn --daemon stop nodemanager && /opt/hadoop/bin/yarn --daemon start nodemanager
turn-on-shufflehandler-debug-logs

#Record start timestamps from each log file (RM / NM)
#-->Memorize top of log of RM / NM, cut the log file from there
awk '{print $2}' < /opt/hadoop/logs/hadoop-systest-nodemanager-$HOSTNAME.log | tail -n1 > $TC_RESULT_DIR/start_timestamp
echo "Recorded start timestamp of NM on host $HOSTNAME: $(cat /$TC_RESULT_DIR/start_timestamp)"