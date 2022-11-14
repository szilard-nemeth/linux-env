#!/bin/bash

set -x
tc=$1
TC_RESULT_DIR="$2"

#Record end timestamps from each log file (RM / NM)
#-->Memorize top of log of RM / NM, cut the log file from there
awk '{print $2}' < /opt/hadoop/logs/hadoop-systest-resourcemanager-$HOSTNAME.log | tail -n1 > $TC_RESULT_DIR/end_timestamp
START_TS=$(cat $TC_RESULT_DIR/start_timestamp)
END_TS=$(cat $TC_RESULT_DIR/end_timestamp)
echo "Recorded end timestamp of RM on host $HOSTNAME: $END_TS"

# Cut RM / NM logs + Copy container logs to TC_RESULT_DIR
awk -v start=$START_TS -v end=$END_TS '$2 >= start && $2 <= end {print;}' < /opt/hadoop/logs/hadoop-systest-resourcemanager-$HOSTNAME.log > $TC_RESULT_DIR/resourcemanager-cut.log

LATEST_APP_ID=$(/opt/hadoop/bin/yarn app -list -appStates FINISHED 2>/dev/null | cut -d ' ' -f1 | grep application | sort -r | head -n1)
echo $LATEST_APP_ID > $TC_RESULT_DIR/application_id
#Alternatively, parse from client logs: 
#YarnClientImpl: Submitted application application_1624999918352_0002



tar czf ~/tc-result-$tc-$HOSTNAME-resourcemanager.tar.gz -C $TC_RESULT_DIR .