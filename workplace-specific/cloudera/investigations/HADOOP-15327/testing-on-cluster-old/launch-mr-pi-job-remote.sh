#!/bin/bash

tc=$1

set -x
#Launch pi job
JVM_OPTS="-Dmapreduce.reduce.log.level=DEBUG,console";
MY_HADOOP_VERSION=3.4.0-SNAPSHOT;
pushd /opt/hadoop;
bin/yarn jar ./share/hadoop/mapreduce/hadoop-mapreduce-examples-$MY_HADOOP_VERSION.jar pi $JVM_OPTS 2 1000
popd;