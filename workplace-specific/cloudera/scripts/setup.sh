#!/usr/bin/env bash

#================Setup locations================
CLOUDERA_DEV_ROOT="$HOME/development/cloudera/"
CLOUDERA_HADOOP_ROOT="$CLOUDERA_DEV_ROOT/hadoop/"
HADOOP_MVN_DIR="$HOME/development/apache/hadoop-maven/"
HADOOP_DEV_DIR="$HOME/development/apache/hadoop/"
export DEX_DEV_ROOT="$HOME/development/cloudera/cde/dex/"

CLOUDERA_DIR="$HOME_LINUXENV_DIR/workplace-specific/cloudera/"
export CLOUDERA_DIR

CLOUDERA_TASKS_DIR="$HOME/development/my-repos/knowledge-base-private/cloudera/tasks"
CLOUDERA_TASKS_CDE_DIR="$CLOUDERA_TASKS_DIR/cde"
export CLOUDERA_TASKS_DIR
export CLOUDERA_TASKS_CDE_DIR
#===============================================

#export PATH="/usr/local/opt/protobuf@2.5/bin:$PATH"
export PATH="/Users/snemeth/.local/bin:$PATH"

#CM build specific settings
export MAVEN_OPTS='-Xmx5000m'
export TARGETROOT=
export MVN_NO_DOCKER=1

#Setup PATH
PATH=$PATH:$HOME/development/other-repos/util-scripts
PATH=$PATH:$HOME/development/cloudera/dist_test/bin

if is-platform-macos
then
    PATH=$PATH:$HOME/Library/Python/2.7/bin
    PATH=$PATH:$HOME/Library/Python/3.8/bin
    PATH=$PATH:/Applications/CMake.app/Contents/bin
fi

PATH=$PATH:$HOME/.cargo/bin