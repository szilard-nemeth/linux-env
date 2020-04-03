#!/usr/bin/env bash

cd /home/systest;

echo "Unpacking YARN to /home/systest/$MY_HADOOP_VERSION/"
tar xzvf hadoop-${MY_HADOOP_VERSION}.tar.gz;
cd hadoop-${MY_HADOOP_VERSION};

echo "Running YARN-Cluster-Setup script..."
../YARN-Cluster-Setup/setup.sh;

echo "Making backup of original YARN config to /home/systest/hadoop-yarn-config-backup/"
mkdir /home/systest/hadoop-yarn-config-backup/
cp -rf /opt/hadoop/etc/hadoop /home/systest/hadoop-yarn-config-backup/

##PLACEHOLDER: scp CONFIG FILES to RM / NM cluster nodes
if [ ! -f ${YARN_CONFIG_SCRIPT} ]; then
    echo "Executing YARN config script: $YARN_CONFIG_SCRIPT"
    /bin/bash ${YARN_CONFIG_SCRIPT}
fi


echo "Restarting YARN..."
/opt/hadoop/sbin/stop-yarn.sh && /opt/hadoop/sbin/start-yarn.sh;


LOG_PACKAGE="org.apache.hadoop.yarn.server.resourcemanager"
echo "Turning on DEBUG log on package $LOG_PACKAGE"
/opt/hadoop/bin/yarn daemonlog -setlevel `hostname`:8088 ${LOG_PACKAGE} DEBUG;
/opt/hadoop/bin/hdfs dfsadmin -safemode leave