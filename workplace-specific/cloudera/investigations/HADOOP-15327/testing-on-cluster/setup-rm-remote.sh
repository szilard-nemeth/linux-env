#!/bin/bash

set -x
tc=$1
TC_RESULT_DIR="$2"
rmhost=$3

#Fix RM hostname in yarn-site.xml
sudo sed -i -e 's/master.cloudera.com/'$rmhost'/g' /opt/hadoop/etc/hadoop/yarn-site.xml
cp /opt/hadoop/etc/hadoop/yarn-site.xml $TC_RESULT_DIR/yarn-site.xml


#Restart RM
/opt/hadoop/bin/yarn --daemon stop resourcemanager && /opt/hadoop/bin/yarn --daemon start resourcemanager

#Record start timestamps from each log file (RM / NM)
#-->Memorize top of log of RM / NM, cut the log file from there
awk '{print $2}' < /opt/hadoop/logs/hadoop-systest-resourcemanager-$HOSTNAME.log | tail -n1 > $TC_RESULT_DIR/start_timestamp
echo "Recorded start timestamp of RM on host $HOSTNAME: $(cat /$TC_RESULT_DIR/start_timestamp)"
sleep 10