#!/bin/bash

echo "Passed arguments to hadoop-env.sh: $@"
HADOOP_DIR=$1
export HADOOP_HOME=${HADOOP_DIR}/$(cd ${HADOOP_DIR}; ls -d hadoop-dist/target/hadoop-*-SNAPSHOT)
echo "HADOOP_HOME is: $HADOOP_HOME"

export PATH=${HADOOP_HOME}/bin:$PATH

# hadoop-conf was copied from ./hadoop-yarn-project/hadoop-yarn/conf/
#make a copy of the template as opening a new shell would overwrite them
#if in-place modifications were performed on config files
cp -R ${CLOUDERA_DIR}/config/hadoop/hadoop-conf-template ${CLOUDERA_DIR}/config/hadoop/hadoop-conf
export HADOOP_CONF_DIR=${CLOUDERA_DIR}/config/hadoop/hadoop-conf
echo "Hadoop config directory is: $HADOOP_CONF_DIR"

#update $version with current pom.xml version in mapred-site.xml
pushd ${HADOOP_DIR} > /dev/null
MVN_VER=$(echo '${project.version}' | mvn help:evaluate 2> /dev/null | grep -v '^[[]')
sed -i "s+target/hadoop-.*+target/hadoop-$MVN_VER</value>+" ${HADOOP_CONF_DIR}/mapred-site.xml
popd > /dev/null

export HADOOP_MAPRED_HOME=${HADOOP_HOME}
export HADOOP_COMMON_HOME=${HADOOP_HOME}
export HADOOP_HDFS_HOME=${HADOOP_HOME}
export YARN_HOME=${HADOOP_HOME}