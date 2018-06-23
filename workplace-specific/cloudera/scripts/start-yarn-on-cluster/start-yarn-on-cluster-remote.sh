#!/usr/bin/env bash

cd /home/systest;
tar xzvf hadoop-$MY_HADOOP_VERSION.tar.gz;
cd hadoop-$MY_HADOOP_VERSION;
../YARN-Cluster-Setup/setup.sh;
/opt/hadoop/bin/yarn daemonlog -setlevel `hostname`:8088 org.apache.hadoop.yarn.server.resourcemanager DEBUG;
/opt/hadoop/bin/hdfs dfsadmin -safemode leave