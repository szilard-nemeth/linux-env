#!/usr/bin/env bash
#set -x

NEW_JAR_PATH="/home/systest/$SRC_JAR_FILENAME"
MD5_NEW_JAR=$(md5sum $NEW_JAR_PATH)
echo "MD5 sum of copied jar on `hostname`: $MD5_NEW_JAR"


#find destination path
CDH_JARS_LOCATION=/opt/cloudera/parcels/CDH/jars
DST_JAR_PATH=$(find ${CDH_JARS_LOCATION} -iname "$SRC_JAR_FILENAME")

if [ -z "$DST_JAR_PATH" ]; then
    echo "No result files found on cluster in $CDH_JARS_LOCATION for filename $SRC_JAR_FILENAME!"
    echo "Command was: find ${CDH_JARS_LOCATION} -iname \"$SRC_JAR_FILENAME\""
    exit -2
fi

NUMBER_OF_RESULTS=$(echo "$DST_JAR_PATH" | wc -l)
if [ $NUMBER_OF_RESULTS -gt 1 ]; then
	echo "Two or more files found for filename $SRC_JAR_FILENAME";
	echo "File list: ";
	echo "$DST_JAR_PATH";
	exit -1
fi


#make backup of original jar
DST_JAR_BACKUP_PATH="/home/systest/$SRC_JAR_FILENAME-original"
echo "Making backup of jar from $DST_JAR_PATH to $DST_JAR_BACKUP_PATH"
sudo cp $DST_JAR_PATH "$DST_JAR_BACKUP_PATH"


#replace jar with new jar
echo "Copying file: $NEW_JAR_PATH --> $DST_JAR_PATH"
sudo cp $NEW_JAR_PATH $DST_JAR_PATH


#print location file with ls + md5 sum
echo "New file info: "
ls -la $DST_JAR_PATH

echo "MD5 sum of new jar file: $(md5sum $DST_JAR_PATH)"

# set +x