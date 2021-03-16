#!/bin/bash

HADOOP_BUILD_ROOT="/Users/snemeth/development/cloudera/hadoop/"
INVESTIGATION_BASEDIR="$LINUX_ENV_REPO/workplace-specific/cloudera/investigations/YARN-10427"
HADOOP_VERSION=$(cd $HADOOP_BUILD_ROOT && echo '${project.version}' | mvn help:evaluate 2> /dev/null | grep -v '^[[]')
MVN_BUILD_COMMAND="mvn clean package -s $HOME/.m2/settings-cdpd.xml -Pdist -DskipTests -Dmaven.javadoc.skip=true"

#REMOTE-HOST SPECIFIC
CLUSTER_HOST1="root@snemeth-fips2-1.vpc.cloudera.com"
REMOTE_BASEDIR="/root/YARN-10427-downstream"