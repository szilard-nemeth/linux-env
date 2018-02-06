#!/usr/bin/env bash


function start-hadoop-internal {
    HADOOP_DIR=$1

    HADOOP_SCRIPTS_DIR=$CLOUDERA_DIR/scripts/hadoop/
    HADOOP_ENV_SCRIPT="$HADOOP_SCRIPTS_DIR/hadoop-env.sh"
    echo "Sourcing $HADOOP_ENV_SCRIPT"
    source $HADOOP_ENV_SCRIPT $HADOOP_DIR

    cd $HADOOP_DIR

    echo "Starting Hadoop..."
    $HADOOP_SCRIPTS_DIR/start-hadoop.sh
}

function start-hadoop {
    start-hadoop-internal $HADOOP_MVN_DIR
}

function start-hadoop-dev {
    start-hadoop-internal $HADOOP_DEV_DIR
}