#!/bin/bash


function start-sls() {
	set -x
	set -e
	echo "Arguments:"
	echo $@
	if [ $# -ne 2 ]; then
    	echo "Usage: $0 [hadoop-version] [investigation basedir]"
    	echo "Example: $0 $(pwd)/ 3.3.0 /root/YARN-10427"
    	exit 1
  	fi
  	
  	HADOOP_VERSION="$1"
  	INVESTIGATION_BASEDIR="$2"
	echo "STARTING SLS SCRIPT..."
	
	#Cleanup
	HADOOP_DIR=$INVESTIGATION_BASEDIR/hadoop-untarred
	echo "Removing & Recreating Hadoop-dist dir: $HADOOP_DIR"
	rm -rf $HADOOP_DIR && mkdir $HADOOP_DIR && cd $HADOOP_DIR;
	echo "Extracting Hadoop-dist to $HADOOP_DIR/"
	tar xzf $INVESTIGATION_BASEDIR/hadoop-$HADOOP_VERSION.tar.gz


	HADOOP_ROOT="$HADOOP_DIR/hadoop-$HADOOP_VERSION/"
	ETC_HADOOP_DIR="$HADOOP_ROOT/etc/hadoop/"
	CONF_SRC_DIR="$INVESTIGATION_BASEDIR/config"
	SCRIPTS_DIR="$INVESTIGATION_BASEDIR/scripts"
	LOGS_DIR="$INVESTIGATION_BASEDIR/logs"

	echo "Copying configs to $ETC_HADOOP_DIR"
	copy-config-to-hadoop-dir "inputsls.json"
	copy-config-to-hadoop-dir "mapred-site.xml"
	copy-config-to-hadoop-dir "yarn-site.xml"
	copy-config-to-hadoop-dir "fair-scheduler.xml"
	copy-config-to-hadoop-dir "sls-runner.xml"
	copy-config-to-hadoop-dir "log4j.properties"

	#Create SLS log folder and output.log file
	CURRDATE="$(date +%Y%m%d_%H%M%S)";
	SLS_OUT="$LOGS_DIR/slsrun-out-$CURRDATE";
	SLS_LOG="$SLS_OUT/output.log";
	mkdir -p $SLS_OUT;
	touch $SLS_LOG;

	JAVA_HOME_VAL="/usr/java/jdk1.8.0_231"
	echo "Setting JAVA_HOME to $JAVA_HOME_VAL"
	JAVA_HOME=/usr/java/jdk1.8.0_231;
	export JAVA_HOME;
	$HADOOP_ROOT/share/hadoop/tools/sls/bin/slsrun.sh \
	--tracetype=SLS \
	--tracelocation=$CONF_SRC_DIR/inputsls.json \
	--output-dir=$SLS_OUT \
	--print-simulation \
	--track-jobs=job_1,job_2,job_3,job_4,job_5,job_6,job_7,job_8,job_9,job_10 |& tee $SLS_LOG
}

function copy-config-to-hadoop-dir() {
	echo "Copying config $CONF_SRC_DIR/$1 to $ETC_HADOOP_DIR"
	cp $CONF_SRC_DIR/$1 $ETC_HADOOP_DIR
}

function grep-in-latest-logs() {
	LATEST_SLS_OUT_DIR=$(ls -td -- $LOGS_DIR/slsrun* | head -n 1)
	SLS_LOG_FILE="$LATEST_SLS_OUT_DIR/output.log"
	cd $LATEST_SLS_OUT_DIR
	mkdir ./grepped

	echo "Latest logs: $LATEST_SLS_OUT_DIR"
	echo "Grepping into $LATEST_SLS_OUT_DIR/grepped..."

	full_app_id=$(cat $LATEST_SLS_OUT_DIR/jobruntime.csv | cut -d ',' -f1 | sort | uniq --repeated | head -n 1)
	#TODO Ensure if there's any dupe app id

	simple_app_id=$(echo $full_app_id | cut -d '_' -f2-)
	am_container_id="container_${simple_app_id}_01_000001"
	grep "$full_app_id" $SLS_LOG_FILE > ./grepped/$full_app_id.log
	grep "$simple_app_id" $SLS_LOG_FILE  > ./grepped/$simple_app_id.log
	grep "$am_container_id" $SLS_LOG_FILE > ./grepped/$am_container_id.log
}


start-sls "$@"
grep-in-latest-logs