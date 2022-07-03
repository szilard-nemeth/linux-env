## 0. kinit
```
/usr/bin/kinit -k -t /home/hrt_qa/hadoopqa/keytabs/hrt_qa.headless.keytab -l 2d -r 3d hrt_qa@YARN-UYJ.L2OV-M7VS.INT.CLDR.WORK
```

## 1. Create result dir for local commands
`mkdir -p ~/yarntest_snemeth`


## 2. Set up common variables
```
EXAMPLES_JAR=/opt/cloudera/parcels/CDH/lib/hadoop-mapreduce/hadoop-mapreduce-examples.jar
HADOOP_BIN=/opt/cloudera/parcels/CDH/bin/hadoop
CLOUDBREAK_KEY=~/.ssh/ycloud_priv_key 
```

## 3. Set up input dir variables for HDFS
```
BASE_DIR=/user/hrt_qa/test_mapred_ha/
INPUT_DIR=$BASE_DIR/wordcount_input_normal
INPUT_DIR_SMALL=$BASE_DIR/wordcount_input_small
INPUT_DIR_MEDIUM=$BASE_DIR/wordcount_input_medium
OUTPUT_DIR=$BASE_DIR/test_mapred_ha_single_job_nn-jobtracker-1-min
```

## 4.1 Execute randomtextwriter to generate input data for wordcount - Normal data size
```
$HADOOP_BIN jar $EXAMPLES_JAR randomtextwriter "-Dmapreduce.randomtextwriter.totalbytes=26843545600" $INPUT_DIR 2>&1 | tee ~/yarntest_snemeth/client-log-randomtextwriter-normal.txt
```

## 4.2 Execute randomtextwriter to generate input data for wordcount - Smaller data size
```
$HADOOP_BIN jar $EXAMPLES_JAR randomtextwriter "-Dmapreduce.randomtextwriter.totalbytes=1342177280" $INPUT_DIR_SMALL 2>&1 | tee 
~/yarntest_snemeth/client-log-randomtextwriter-small.txt
```


## 4.3 Execute randomtextwriter to generate input data for wordcount - Medium data size
```
$HADOOP_BIN jar $EXAMPLES_JAR randomtextwriter "-Dmapreduce.randomtextwriter.totalbytes=13421772800" $INPUT_DIR_MEDIUM 2>&1 | tee ~/yarntest_snemeth/client-log-randomtextwriter-medium.txt
```


## 5.1 Execute wordcount (Rahul's original command)
```
$HADOOP_BIN jar $EXAMPLES_JAR wordcount "-Dmapreduce.reduce.input.limit=-1" "-Dyarn.resourcemanager.am.max-attempts=10"  "-Dmapreduce.am.max-attempts=10" $INPUT_DIR $OUTPUT_DIR  2>&1 | tee ~/yarntest_snemeth/client-log-wordcount-normal.txt
```

## 5.2 Execute wordcount - Specify mapper memory / vcores
```
$HADOOP_BIN jar $EXAMPLES_JAR wordcount "-Dmapreduce.reduce.input.limit=-1" "-Dyarn.resourcemanager.am.max-attempts=10"  "-Dmapreduce.am.max-attempts=10" "-Dmapreduce.map.memory.mb=1024" "-Dmapreduce.map.vcores=1" $INPUT_DIR $OUTPUT_DIR  2>&1 | tee ~/yarntest_snemeth/client-log-wordcount-normal-modcommand.txt
```

## Save logs and other files
```
scp -i $CLOUDBREAK_KEY cloudbreak@172.27.53.65:yarntest_snemeth/mapred_single_wordcount_mod_command.txt ~/Downloads/_work/COMPX-8334/investigation_3/
scp -i $CLOUDBREAK_KEY cloudbreak@172.27.173.14:aggregated-logs-yarn_application_1647876814131_0501 .
scp -i $CLOUDBREAK_KEY cloudbreak@172.27.89.71:application_1652361433881_0023 .
```

## Save ResourceManager log to local machine
```
scp -i $CLOUDBREAK_KEY cloudbreak@172.27.183.70:/var/log/hadoop-yarn/hadoop-cmf-yarn-RESOURCEMANAGER-yarn-gtinhh-master0.yarn-uyj.l2ov-m7vs.int.cldr.work.log.out ~/Downloads/_work/COMPX-8334/investigation_6/
```

## Other commands
```
Client config: 
/etc/hadoop/conf.cloudera.yarn


CLOUDBREAK_KEY=~/.ssh/ycloud_priv_key;
ssh 172.27.53.65 -l cloudbreak -i $CLOUDBREAK_KEY "sudo grep 46789 /var/run/cloudera-scm-agent/process/ -R"
```