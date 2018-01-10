#!/bin/bash

export HADOOP_HOME=$HADOOP_MVN_DIR/$(cd $HADOOP_MVN_DIR; ls -d hadoop-dist/target/hadoop-*-SNAPSHOT)
export PATH=$HADOOP_HOME/bin:$PATH

# hadoop-conf is copied from ./hadoop-yarn-project/hadoop-yarn/conf/
export HADOOP_CONF_DIR=$CLOUDERA_DIR/config/hadoop/hadoop-conf

#update $version with current pom.xml version in mapred-site.xml
pushd $HADOOP_MVN_DIR
MVN_VER=$(echo '${project.version}' | mvn help:evaluate 2> /dev/null | grep -v '^[[]')
sed -i "s+target/hadoop-.*+target/hadoop-$MVN_VER</value>+" $HADOOP_CONF_DIR/mapred-site.xml
popd

export HADOOP_MAPRED_HOME=$HADOOP_HOME
export HADOOP_COMMON_HOME=$HADOOP_HOME
export HADOOP_HDFS_HOME=$HADOOP_HOME
export YARN_HOME=$HADOOP_HOME