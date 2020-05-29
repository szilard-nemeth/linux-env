#!/usr/bin/env bash
#set -x

NEW_JAR_PATH="/home/systest/$SRC_JAR_FILENAME"
MD5_NEW_JAR=$(md5sum ${NEW_JAR_PATH})
echo "MD5 sum of copied jar on `hostname`: $MD5_NEW_JAR"


#find destination path

##Old path
#CDH_JARS_LOCATION=/opt/cloudera/parcels/CDH/jars

##New path
CDH_JARS_LOCATION=/opt/cloudera/cm/lib/cdh7
DST_JAR_PATH=$(find ${CDH_JARS_LOCATION} -iname "$SRC_JAR_FILENAME")

if [[ -z "$DST_JAR_PATH" ]]; then
    echo "No target files found on cluster in $CDH_JARS_LOCATION for filename $SRC_JAR_FILENAME!"
    echo "Command was: find ${CDH_JARS_LOCATION} -iname \"$SRC_JAR_FILENAME\""
    
    #Fallback
    #Example: find /opt/cloudera/parcels/CDH/jars -iname "hadoop-yarn-server-resourcemanager*"
    echo "Fallback: Trying to find target file for filename / pattern: $JAR_FILE_NAME"
    DST_JAR_PATH=$(find ${CDH_JARS_LOCATION} -iname "$JAR_FILE_NAME")
    if [[ -z "$DST_JAR_PATH" ]]; then
        echo "No target files found on cluster in $CDH_JARS_LOCATION for filename $JAR_FILE_NAME!"
        echo "Command was: find ${CDH_JARS_LOCATION} -iname \"$JAR_FILE_NAME\""
        exit -2
    fi
    SRC_JAR_FILENAME="$JAR_FILE_NAME"
fi

NUMBER_OF_RESULTS=$(echo "$DST_JAR_PATH" | wc -l)
if [ ${NUMBER_OF_RESULTS} -gt 1 ]; then
    echo "Two or more files found for filename $SRC_JAR_FILENAME";
    echo "File list: ";
    echo "$DST_JAR_PATH";
    exit -1
fi


#make backup of original jar
DATE_OF_BACKUP=`date +%F-%H%M%S`
DST_JAR_BACKUP_PATH="/home/systest/$SRC_JAR_FILENAME-original-$DATE_OF_BACKUP"
echo "Making backup of jar from $DST_JAR_PATH to $DST_JAR_BACKUP_PATH"
sudo cp ${DST_JAR_PATH} "$DST_JAR_BACKUP_PATH"


#replace jar with new jar
echo "Copying file: $NEW_JAR_PATH --> $DST_JAR_PATH"
sudo cp ${NEW_JAR_PATH} ${DST_JAR_PATH}


#print location file with ls + md5 sum
echo "New file info: "
ls -la ${DST_JAR_PATH}

echo "MD5 sum of new jar file: $(md5sum ${DST_JAR_PATH})"

# set +x