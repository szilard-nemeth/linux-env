#!/bin/bash

currdate=$(date +%Y%m%d_%H%M%S)
log_dir="/tmp/HADOOP-15327-testing/"
mkdir -p "$log_dir"
log_file="$log_dir/run-testcases.log"
echo "Logs will be saved to $log_file"
echo "Use this command to follow the contents of the log file: "
echo "tail -f $log_file"

./run-testcases.sh 2>&1 | tee $log_file