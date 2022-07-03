## 0. kinit
```
kinit -k -t /cdep/keytabs/systest.keytab systest -l 30d
```

## 1. Create result dir for local commands
`mkdir -p ~/yarntest_snemeth`


## 2. Set up common variables
```
EXAMPLES_JAR=/opt/cloudera/parcels/CDH/lib/hadoop-mapreduce/hadoop-mapreduce-examples.jar
HADOOP_BIN=/opt/cloudera/parcels/CDH/bin/hadoop
SYSTEST_SSH_KEY=~/.ssh/nightly_id_rsa
```

## 3. Set up input dir variables for HDFS
```
hdfs dfs -mkdir /user/systest/test_mapred_ha
BASE_DIR=/user/systest/test_mapred_ha
INPUT_DIR=$BASE_DIR/wordcount_input_normal
OUTPUT_DIR=$BASE_DIR/test_mapred_ha_single_job_nn-jobtracker-1-min
```

## 4.Execute randomtextwriter to generate input data for wordcount - Normal data size
```
$HADOOP_BIN jar $EXAMPLES_JAR randomtextwriter "-Dmapreduce.randomtextwriter.totalbytes=26843545600" $INPUT_DIR 2>&1 | tee ~/yarntest_snemeth/client-log-randomtextwriter-normal.txt
```

## 5. Execute wordcount
```
$HADOOP_BIN jar $EXAMPLES_JAR wordcount "-Dmapreduce.reduce.input.limit=-1" "-Dyarn.resourcemanager.am.max-attempts=10"  "-Dmapreduce.am.max-attempts=10" $INPUT_DIR $OUTPUT_DIR  2>&1 | tee ~/yarntest_snemeth/client-log-wordcount-normal.txt
```

## 6. Save logs and other files
```
scp -i $SYSTEST_SSH_KEY -r systest@pvc-dwx-rp-1.pvc-dwx-rp.root.hwx.site:yarntest_snemeth/ ~/Downloads/_work/COMPX-8334/investigation_8_pvc_alpha/
```
