#!/usr/bin/env bash

function start-hadoop-example-job {
set -x
    HADOOP_PARAMETERS=$1
    #example parameters: 'pi -Dmapreduce.framework.name=yarn -Dmapreduce.map.resource.gpu=5000m 10 100'

    HADOOP_DIR="$HOME/development/apache/hadoop-maven/"
    HADOOP_DIST_DIR="$HADOOP_DIR/hadoop-dist/"
    HADOOP_VERSION="3.1.0-SNAPSHOT"

    $HADOOP_DIST_DIR/target/hadoop-$HADOOP_VERSION/bin/hadoop jar \
    $HADOOP_DIST_DIR/target/hadoop-$HADOOP_VERSION/share/hadoop/mapreduce/hadoop-mapreduce-examples-$HADOOP_VERSION.jar $1
}