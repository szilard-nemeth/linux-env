#!/bin/bash

#TODO Move to https://github.com/szilard-nemeth/linux-backup-scripts
#arg1: destination directory of save
#arg2: redis hash key

#TODO check arguments are present
#TODO pip install rdb.py instead of referring to it with absolute path

function redis-backup() {
    BACKUP_SRC_LOCATION=/var/redis/6379/dump.rdb
    DEST=$1
    REDIS_HASH_KEY=$2
    
    rm /tmp/rediscliout
    
    #Save ids to file
    redis-cli save
    
    cp $BACKUP_SRC_LOCATION $1
    
    #read contents
    python /usr/local/redis-rdb-tools/build/lib.linux-x86_64-2.7/rdbtools/cli/rdb.py --command json $BACKUP_SRC_LOCATION
    redis-cli --csv HGETALL $REDIS_HASH_KEY > /tmp/rediscliout
    cp /tmp/rediscliout $DEST
}