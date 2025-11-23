#!/usr/bin/env bash

#================Setup locations================
CLOUDERA_DEV_ROOT="$HOME/development/cloudera/"
CLOUDERA_HADOOP_ROOT="$CLOUDERA_DEV_ROOT/hadoop/"
HADOOP_MVN_DIR="$HOME/development/apache/hadoop-maven/"
HADOOP_DEV_DIR="$HOME/development/apache/hadoop/"
export CDE_DEV_ROOT="$HOME/development/cloudera/cde/"
export DEX_DEV_ROOT="$CDE_DEV_ROOT/dex/"
export DEX_RTCATALOG_FILE="$DEX_DEV_ROOT/pkg/control-plane/service/catalog-entries.json"

CLOUDERA_DIR="$HOME_LINUXENV_DIR/workplace-specific/cloudera/"
export CLOUDERA_DIR

CLOUDERA_TASKS_DIR="$HOME/development/my-repos/knowledge-base-private/cloudera/tasks"
CLOUDERA_TASKS_CDE_DIR="$CLOUDERA_TASKS_DIR/cde"
export CLOUDERA_TASKS_DIR
export CLOUDERA_TASKS_CDE_DIR
#===============================================
#add_to_path_directly "/usr/local/opt/protobuf@2.5/bin"


#CM build specific settings
export MAVEN_OPTS='-Xmx5000m'
export TARGETROOT=
export MVN_NO_DOCKER=1

#Setup PATH
add_to_path_directly $HOME/development/other-repos/util-scripts
add_to_path_directly $HOME/development/cloudera/dist_test/bin

if is-platform-macos
then
    add_to_path_directly $HOME/Library/Python/2.7/bin
    add_to_path_directly $HOME/Library/Python/3.8/bin
    add_to_path_directly /Applications/CMake.app/Contents/bin
fi

add_to_path_directly $HOME/.cargo/bin