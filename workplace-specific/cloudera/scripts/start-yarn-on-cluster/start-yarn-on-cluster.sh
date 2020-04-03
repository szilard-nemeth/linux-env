#!/usr/bin/env bash

pushd ~/development/apache/hadoop;
MY_HADOOP_VERSION=$(mvn org.apache.maven.plugins:maven-help-plugin:2.1.1:evaluate \
    -Dexpression=project.version 2>/dev/null |grep -Ev '(^\[|Download\w+:)')

CLOUDERA_HOSTNAME=$1

echo "Bulding upstream YARN..."
mvn clean package -Pdist -DskipTests -Dmaven.javadoc.skip=true && scp hadoop-dist/target/hadoop-${MY_HADOOP_VERSION}.tar.gz systest@${CLOUDERA_HOSTNAME}:~

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Running start-yarn-on-cluster-remote.sh on $CLOUDERA_HOSTNAME..."
ssh systest@${CLOUDERA_HOSTNAME} MY_HADOOP_VERSION="$MY_HADOOP_VERSION" 'bash -s' < "$DIR/start-yarn-on-cluster-remote.sh"