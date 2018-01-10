#!/usr/bin/env bash


function start-hadoop {
    HADOOP_SCRIPTS_DIR=$CLOUDERA_DIR/scripts/hadoop/
    HADOOP_ENV_SCRIPT="$HADOOP_SCRIPTS_DIR/hadoop-env.sh"
    echo "Sourcing $HADOOP_ENV_SCRIPT"
    source $HADOOP_ENV_SCRIPT

    cd $HADOOP_MVN_DIR

    echo "Starting Hadoop..."
    $HADOOP_SCRIPTS_DIR/start-hadoop.sh
}