#!/bin/bash
. ./setup-vars.sh
#set -x
GREP_FOR=$1
DEST_FILE_NAME=$2

LATEST_SLS_OUT_DIR=$(ls -td -- $INVESTIGATION_BASEDIR/logs/slsrun* | head -n 1)
SLS_LOG_FILE="$LATEST_SLS_OUT_DIR/output.log"
GREP_DEST_DIR="$LATEST_SLS_OUT_DIR/grepped/"

grep "$GREP_FOR" $SLS_LOG_FILE > $GREP_DEST_DIR/$DEST_FILE_NAME