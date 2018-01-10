#!/usr/bin/env bash

function start-hadoop-example-job {
    HADOOP_PARAMETERS=$1
    #example parameters: 'pi -Dmapreduce.framework.name=yarn -Dmapreduce.map.resource.gpu=5000m 10 100'

    HADOOP_DIST_DIR="$HADOOP_MVN_DIR/hadoop-dist/"

    #update $version with current pom.xml version in mapred-site.xml
    pushd $HADOOP_MVN_DIR
    HADOOP_VERSION=$(echo '${project.version}' | mvn help:evaluate 2> /dev/null | grep -v '^[[]')
    popd

    set -x
    $HADOOP_DIST_DIR/target/hadoop-$HADOOP_VERSION/bin/hadoop jar \
    $HADOOP_DIST_DIR/target/hadoop-$HADOOP_VERSION/share/hadoop/mapreduce/hadoop-mapreduce-examples-$HADOOP_VERSION.jar $1
    set +x
}