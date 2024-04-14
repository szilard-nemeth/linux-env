#!/usr/bin/env bash

function stop-hadoop {
    HADOOP_SCRIPTS_DIR=${CLOUDERA_DIR}/scripts/hadoop/

    echo "Stopping Hadoop..."
    ${HADOOP_SCRIPTS_DIR}/stop-hadoop.sh
    sleep 2;
    jps;
}