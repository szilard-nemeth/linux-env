#!/usr/bin/env bash

DFS_DATA_DIR=/private/tmp/hadoop-szilardnemeth/dfs/data
if [ -d "$DFS_DATA_DIR" ]; then
  rm -rf ${DFS_DATA_DIR};
fi

hdfs namenode -format
hdfs namenode > /tmp/nn.log 2>&1 &
hdfs datanode > /tmp/dn.log 2>&1 &
yarn resourcemanager > /tmp/rm.log 2>&1 &

yarn nodemanager > /tmp/nm.log 2>&1 &
mapred historyserver > /tmp/hs.log 2>&1 &
