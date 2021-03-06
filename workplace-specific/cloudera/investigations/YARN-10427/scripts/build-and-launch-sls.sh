#! /bin/bash

. ./setup-vars.sh
set -e
#set -x
echo "Building Hadoop in build root: $HADOOP_BUILD_ROOT"
cd $HADOOP_BUILD_ROOT
$MVN_BUILD_COMMAND
ssh $CLUSTER_HOST1 "mkdir -p $REMOTE_BASEDIR"
scp $HADOOP_BUILD_ROOT/hadoop-dist/target/hadoop-$HADOOP_VERSION.tar.gz $CLUSTER_HOST1:$REMOTE_BASEDIR
cd -
./launch-sls.sh