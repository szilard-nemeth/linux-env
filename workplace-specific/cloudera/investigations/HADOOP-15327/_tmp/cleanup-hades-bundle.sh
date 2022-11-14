#! /bin/bash

# UNCOMMENT THESE ONE BY ONE
# dir=/Users/snemeth/development/my-repos/linux-env/workplace-specific/cloudera/investigations/HADOOP-15327/testing-on-cluster-hades/2022_11/hades-results-20221108/session-20221107_115726-without-patch
# dir=/Users/snemeth/development/my-repos/linux-env/workplace-specific/cloudera/investigations/HADOOP-15327/testing-on-cluster-hades/2022_11/hades-results-20221108/session-20221108_084855-with-patch

num_targz=$(find $dir -iname "application_*ccycloud*.tar.gz" -type f | wc -l | tr -s ' ' | cut -d' ' -f2)
num_app_dirs=$(find $dir -iname "application_*ccycloud*" -type d | 	wc -l | tr -s ' ' | cut -d' ' -f2)

if [ "$num_targz" -eq "$num_app_dirs" ]; then
	echo "Removing application tar gz files"
	find $dir -iname "application_*ccycloud*.tar.gz" -type f -exec rm {} \;
fi


# find latest testcase as we want to keep daemonlogs for that one
last_tc=$(find $dir -iname "tc*" -type d | xargs basename | sort -rV | head -n 1)

# Remove dirs
find $dir \( -name "NM_daemonlogs_*" -o -name "RM_daemonlogs_*" \) -type d | grep -v $last_tc | xargs rm -rf

# Remove files
find $dir \( -name "NM_daemonlogs_*" -o -name "RM_daemonlogs_*" \) -type f | grep -v $last_tc | xargs rm -rf