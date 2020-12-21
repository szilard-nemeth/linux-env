#! /bin/bash

. ./setup-vars.sh
set -e
echo "Building Hadoop in build root: $HADOOP_BUILD_ROOT"
cd $HADOOP_BUILD_ROOT
$MVN_BUILD_COMMAND
scp $HADOOP_BUILD_ROOT/hadoop-dist/target/hadoop-$HADOOP_VERSION.tar.gz $CLUSTER_HOST1:$REMOTE_BASEDIR
./launch-sls.sh
cd -