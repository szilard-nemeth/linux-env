#!/usr/bin/env bash

cd /home/systest;
tar xzvf hadoop-$MY_HADOOP_VERSION.tar.gz;
cd hadoop-$MY_HADOOP_VERSION;
../YARN-Cluster-Setup/setup.sh;
cp ~/yarn-site-min0alloc.xml /opt/hadoop/etc/hadoop/yarn-site.xml;
cp ~/fairschedulerconfigs/fair-scheduler-0memmax.xml /opt/hadoop/etc/hadoop/fair-scheduler.xml;
/opt/hadoop/sbin/stop-yarn.sh && /opt/hadoop/sbin/start-yarn.sh;
/opt/hadoop/bin/yarn daemonlog -setlevel `hostname`:8088 org.apache.hadoop.yarn.server.resourcemanager DEBUG;
/opt/hadoop/bin/hdfs dfsadmin -safemode leave