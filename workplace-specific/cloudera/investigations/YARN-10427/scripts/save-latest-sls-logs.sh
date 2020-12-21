#!/bin/bash
. ./setup-vars.sh

sls_dirname=$(ssh $CLUSTER_HOST1 "ls -td -- $REMOTE_BASEDIR/logs/slsrun* | head -n 1")
#TODO exit with error if sls_dirname is empty

SAVE_FROM=$CLUSTER_HOST1:$sls_dirname
SAVE_TO=$INVESTIGATION_BASEDIR/logs
echo "Saving SLS logs from remote host $SAVE_FROM to local dir $SAVE_TO/$sls_dirname"
scp -r $SAVE_FROM $SAVE_TO