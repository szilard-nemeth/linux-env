#!/bin/bash

#setup locations
CLOUDERA_DEV_ROOT="$HOME/development/cloudera/"
CLOUDERA_HADOOP_ROOT="$CLOUDERA_DEV_ROOT/hadoop/"
HADOOP_MVN_DIR="$HOME/development/apache/hadoop-maven/"
HADOOP_DEV_DIR="$HOME/development/apache/hadoop/"


#goto aliases
alias goto-cldr="cd $CLOUDERA_DEV_ROOT"
alias goto-cldr-hadoop="cd $CLOUDERA_HADOOP_ROOT"
alias goto-tasks="cd $HOME/Google Drive File Stream/My Drive/development/tasks/"
alias goto-hadoop="cd $HADOOP_DEV_DIR"
alias goto-hadoop-mvn="cd $HADOOP_MVN_DIR"

#git special commands
alias git-mybranches="git branch | grep 'own-'"
alias gerrit-branches5="git br -r | grep gerrit | grep -e '5.1\d.*' | cut -d_ -f 2-3 | sort -u | grep -v patch"
alias git-remove-trailing-ws="git diff-tree --no-commit-id --name-only -r HEAD | xargs sed -i 's/[[:space:]]*$//'"
alias j7='export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.7.0_80.jdk/Contents/Home'
alias j8='export JAVA_HOME=/Library/Java//JavaVirtualMachines/jdk1.8.0_151.jdk/Contents/Home'

#YARN-related commands
alias yarn-upstream-gergo="git log --grep grepas --grep 'Gergo Repas' --oneline  | wc -l"
alias yarn-upstream-own="git log --grep snemeth --grep 'Szilard Nemeth' --oneline | wc -l"

alias grind-yarn="export GRIND_MAVEN_FLAGS=-Dmaven-dependency-plugin.version=2.10 && \
rm -rf ~/development/cloudera/dist_test/env/.grind/cache/ && \
goto-hadoop-mvn && \
mvn clean install -DskipTests -Dmaven.javadoc.skip=true && \
cd hadoop-yarn-project && \
grind --verbose test --java-version 8"

alias grind-yarn-exceptions="grind --verbose test --java-version 8 \
 -e TestHBaseStorageFlowActivity \
 -e TestHBaseStorageFlowRun \
 -e TestHBaseStorageFlowRunCompaction \
 -e TestHBaseTimelineStorageApps \
 -e TestHBaseTimelineStorageDomain \
 -e TestHBaseTimelineStorageEntities \
 -e TestHBaseTimelineStorageSchema"