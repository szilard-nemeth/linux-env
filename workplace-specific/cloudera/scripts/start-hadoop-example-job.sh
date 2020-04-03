#!/usr/bin/env bash

function start-hadoop-example-job-internal {
    HADOOP_DIR=$1
    shift;
    HADOOP_PARAMETERS=$@
    #example parameters: 'pi -Dmapreduce.framework.name=yarn -Dmapreduce.map.resource.gpu=5000m 10 100'

    HADOOP_DIST_DIR="$HADOOP_DIR/hadoop-dist/"

    HADOOP_SCRIPTS_DIR=${CLOUDERA_DIR}/scripts/hadoop/
    HADOOP_ENV_SCRIPT="$HADOOP_SCRIPTS_DIR/hadoop-env.sh"
    echo "Sourcing $HADOOP_ENV_SCRIPT"
    source ${HADOOP_ENV_SCRIPT} ${HADOOP_DIR}


    #update $version with current pom.xml version in mapred-site.xml
    pushd ${HADOOP_DIR} > /dev/null
    HADOOP_VERSION=$(echo '${project.version}' | mvn help:evaluate 2> /dev/null | grep -v '^[[]')
    popd  > /dev/null

    set -x
    ${HADOOP_DIST_DIR}/target/hadoop-${HADOOP_VERSION}/bin/hadoop jar \
    ${HADOOP_DIST_DIR}/target/hadoop-${HADOOP_VERSION}/share/hadoop/mapreduce/hadoop-mapreduce-examples-${HADOOP_VERSION}.jar ${HADOOP_PARAMETERS}
    set +x
}

function start-hadoop-example-job {
    local HADOOP_PARAMS=$@
    start-hadoop-example-job-internal ${HADOOP_MVN_DIR} ${HADOOP_PARAMS}
}

function start-hadoop-example-job-dev {
    local HADOOP_PARAMS=$@
    start-hadoop-example-job-internal ${HADOOP_DEV_DIR} ${HADOOP_PARAMS}
}