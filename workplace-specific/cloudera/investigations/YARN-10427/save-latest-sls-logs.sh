#!/bin/bash

CLUSTER_HOST1="root@snemeth-fips2-1.vpc.cloudera.com"
BASEDIR="$LINUX_ENV_REPO/workplace-specific/cloudera/investigations/YARN-10427"

SAVE_FROM=$CLUSTER_HOST1:$sls_dirname
SAVE_TO=$BASEDIR/logs
echo "Saving SLS logs from $SAVE_FROM to $SAVE_TO"
sls_dirname=$(ssh $CLUSTER_HOST1 "ls -td -- ./slsrun* | head -n 1")
scp -r $SAVE_FROM $SAVE_TO
