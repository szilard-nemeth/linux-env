#!/bin/bash


function start() {
	echo "STARTING SLS SCRIPT..."
	#cleanup hadoop dist dir
	rm -rf hadoop-untarred/ && mkdir hadoop-untarred
	cd /root/hadoop-untarred;
	tar xvzf /root/hadoop-3.1.1.7.2.7.0-SNAPSHOT.tar.gz

	HADOOP_ROOT="/root/hadoop-untarred/hadoop-3.1.1.7.2.7.0-SNAPSHOT/"
	ETC_HADOOP_DIR="$HADOOP_ROOT/etc/hadoop/"
	CONF_SRC_DIR="/root/YARN-10427/config"

	##Copy configs into place
	cp $CONF_SRC_DIR/inputsls.json $ETC_HADOOP_DIR
	cp $CONF_SRC_DIR/mapred-site.xml $ETC_HADOOP_DIR
	cp $CONF_SRC_DIR/yarn-site.xml $ETC_HADOOP_DIR
	cp $CONF_SRC_DIR/fair-scheduler.xml $ETC_HADOOP_DIR
	cp $CONF_SRC_DIR/sls-runner.xml $ETC_HADOOP_DIR
	cp $CONF_SRC_DIR/log4j.properties $ETC_HADOOP_DIR


	CURRDATE="$(date +%Y%m%d_%H%M%S)";
	SLS_OUT="/root/slsrun-out-$CURRDATE";
	SLS_LOG="/root/slsrun-out-$CURRDATE/output.log";
	mkdir -p /root/slsrun-out-$CURRDATE;
	touch $SLS_LOG;

	JAVA_HOME=/usr/java/jdk1.8.0_231;
	export JAVA_HOME;
	/root/hadoop-untarred/hadoop-3.1.1.7.2.7.0-SNAPSHOT/share/hadoop/tools/sls/bin/slsrun.sh --tracetype=SLS --tracelocation=/root/YARN-10427/config/inputsls.json --output-dir=$SLS_OUT --print-simulation --track-jobs=job_1,job_2,job_3,job_4,job_5,job_6,job_7,job_8,job_9,job_10 |& tee $SLS_LOG
}

function greps() {
	LATEST_SLS_OUT_DIR=$(ls -td -- /root/slsrun* | head -n 1)
	cd $LATEST_SLS_OUT_DIR
	mkdir ./grepped

	full_app_id=$(cat $LATEST_SLS_OUT_DIR/jobruntime.csv | cut -d ',' -f1 | sort | uniq --repeated | head -n 1)
	simple_app_id=$(echo $full_app_id | cut -d '_' -f2-)
	am_container_id="container_${simple_app_id}_01_000001"
	grep "$full_app_id" $LATEST_SLS_OUT_DIR/output.log > ./grepped/$full_app_id.log
	grep "$simple_app_id" $LATEST_SLS_OUT_DIR/output.log  > ./grepped/$simple_app_id.log
	grep "$am_container_id" $LATEST_SLS_OUT_DIR/output.log > ./grepped/$am_container_id.log
}


start
greps