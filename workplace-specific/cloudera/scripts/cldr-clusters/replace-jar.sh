#!/usr/bin/env bash
# set -x

if [ $# -ne 3 ]; then
    echo "Usage: replace-jar.sh [filename] [destination hostname] [cloudera hadoop project root>"
    echo "Example: replace-jar.sh '*yarn*resourcemanager*jar' snemeth-sparkyarn2-1.gce.cloudera.com /Users/szilardnemeth/development/cloudera/hadoop/"
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

JAR_FILE_NAME=$1
CLOUDERA_HOSTNAME=$2
CLOUDERA_DEV_ROOT=$3

if [[ "$JAR_FILE_NAME" != *jar ]]
then
    echo "Filename should end with 'jar'";
    exit -1
fi


pushd $CLOUDERA_DEV_ROOT

#inverse grep: do not include lib directories
SRC_JAR_PATH=$(find . \( -iname target ! -iname lib \) -exec find {} -type f \( -iname "$JAR_FILE_NAME" ! -iname "*-tests.jar" \) \; | grep -v "lib")
#SRC_JAR_PATH=$(find . \( -iname target ! -iname lib \) -exec find {} -type f \( -iname "*yarn*resourcemanager*jar" ! -iname "*-tests.jar" \) \;)

NUMBER_OF_RESULTS=$(echo "$SRC_JAR_PATH" | wc -l)
if [ $NUMBER_OF_RESULTS -gt 1 ]
then
	echo "Two or more files found for pattern $JAR_FILE_NAME";
	echo "File list: ";
	echo "$SRC_JAR_PATH";
	exit -1
fi

SRC_JAR_FILENAME=$(basename $SRC_JAR_PATH)
MD5_SRC_JAR=$(md5 $SRC_JAR_PATH)
echo "MD5 sum of source jar file: $MD5_SRC_JAR";
NEW_JAR_PATH="/home/systest/$SRC_JAR_FILENAME"

#scp jar to host
echo "Copying jar file $SRC_JAR_PATH to $CLOUDERA_HOSTNAME:$NEW_JAR_PATH";
scp $SRC_JAR_PATH $CLOUDERA_HOSTNAME:/$NEW_JAR_PATH

echo "Running replace-jar-remote.sh on $CLOUDERA_HOSTNAME..."
ssh $CLOUDERA_HOSTNAME SRC_JAR_FILENAME="$SRC_JAR_FILENAME" 'bash -s' < "$DIR/replace-jar-remote.sh"