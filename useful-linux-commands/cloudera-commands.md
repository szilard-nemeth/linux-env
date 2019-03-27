Start YARN GPU jobs with YAPP
=============================

```sudo -u systest hadoop jar /tmp/__yarn_test__/gpu-0.8-jar-with-dependencies.jar com.cloudera.yapp.gpu.GpuClientMain hdfs:/tmp/__yarn_test__/gpu-0.8-jar-with-dependencies.jar -s 25 -requestedgpus 3```

```sudo -u systest hadoop jar /tmp/__yarn_test__/gpu-0.8-jar-with-dependencies.jar com.cloudera.yapp.gpu.GpuClientMain hdfs:/tmp/__yarn_test__/gpu-0.8-jar-with-dependencies.jar -s 25 -requestedgpus 1```


YARN downstream commands
========================

1. Start distributed shell with resources
```yarn jar /opt/cloudera/parcels/CDH-6.x-1.cdh6.x.p0.858611/jars/hadoop-yarn-applications-distributedshell-3.0.0-cdh6.x-SNAPSHOT.jar -jar /opt/cloudera/parcels/CDH-6.x-1.cdh6.x.p0.858611/jars/hadoop-yarn-applications-distributedshell-3.0.0-cdh6.x-SNAPSHOT.jar -shell_command "nvndia-smi" -container_resources memory-mb=2048,yarn.io/gpu=1```

2. Start sleep job with resources
sudo -u systest hadoop jar /opt/cloudera/parcels/CDH/lib/hadoop-mapreduce/hadoop-mapreduce-client-jobclient-tests.jar sleep -Dmapreduce.job.queuename=root.default -Dmapreduce.reduce.resource.gpu=7 -Dyarn.app.mapreduce.am.resource.gpu=11 -m 1 -r 1 -mt 1 -rt 90000

YARN upstream commands
======================

1. Kill NodeManager on host: 

```
host_to_use="systest@snemeth-testing3-3.vpc.cloudera.com"
pid=$(ssh $host_to_use jps |grep NodeManager | cut -f1 -d' ');ssh $host_to_use kill $pid
```

2. Start NodeManagers on cluster:

```
/opt/hadoop/bin/yarn --config /opt/hadoop/etc/hadoop --workers --daemon start nodemanager
```

Maven commands
==============

1. Build with Maven & replace jar on cluster: 

```mvn clean package -Pdist -DskipTests -Dmaven.javadoc.skip=true && replace-jar.sh '*yarn*resourcemanager*jar' snemeth-gpu-1.vpc.cloudera.com /Users/szilardnemeth/development/cloudera/hadoop/```


2. Maven debugging of Spark test

```./build/mvn -Dmaven.surefire.debug="-Xdebug -Xrunjdwp:transport=dt_socket,server=y,suspend=y,address=8000 -Xnoagent" test -Dcdh.build=true -projects resource-managers/yarn/ -Dsuites='org.apache.spark.deploy.yarn.YarnClusterSuite'```

#-agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=8000