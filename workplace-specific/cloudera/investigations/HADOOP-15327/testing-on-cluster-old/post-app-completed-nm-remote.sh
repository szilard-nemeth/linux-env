#!/bin/bash

set -x
tc=$1
TC_RESULT_DIR="$2"

#Record end timestamps from each log file (RM / NM)
#-->Memorize top of log of RM / NM, cut the log file from there
awk '{print $2}' < /opt/hadoop/logs/hadoop-systest-nodemanager-$HOSTNAME.log | tail -n1 > $TC_RESULT_DIR/end_timestamp
START_TS=$(cat $TC_RESULT_DIR/start_timestamp)
END_TS=$(cat $TC_RESULT_DIR/end_timestamp)
echo "Recorded end timestamp of NM on host $HOSTNAME: $END_TS"

# Cut RM / NM logs & Copy to TC_RESULT_DIR
awk -v start=$START_TS -v end=$END_TS '$2 >= start && $2 <= end {print;}' < /opt/hadoop/logs/hadoop-systest-nodemanager-$HOSTNAME.log > $TC_RESULT_DIR/nodemanager-cut.log

LATEST_APP_ID=$(/opt/hadoop/bin/yarn app -list -appStates FINISHED 2>/dev/null | cut -d ' ' -f1 | grep application | sort -r | head -n1)
echo $LATEST_APP_ID > $TC_RESULT_DIR/application_id
#Alternatively, parse from client logs: 
#YarnClientImpl: Submitted application application_1624999918352_0002

#Copy Container logs to TC_RESULT_DIR
cp -R /tmp/hadoop-logs/$LATEST_APP_ID $TC_RESULT_DIR/app_containers/

#Create tar archive
tar czf ~/tc-result-$tc-$HOSTNAME-nodemanager.tar.gz -C $TC_RESULT_DIR .
#[systest@ccycloud-2 hadoop]$ grep -R org.apache.hadoop.mapreduce.task.reduce /tmp/hadoop-logs/application_1624999918352_0003