Save ids to file
redis-cli save
cp /var/redis/6379/dump.rdb /mnt/raid/samba_share/

read contents
python rdb.py --command json /var/redis/6379/dump.rdb
python /usr/local/redis-rdb-tools/build/lib.linux-x86_64-2.7/rdbtools/cli/rdb.py --command json /var/redis/6379/dump.rdb

redis-cli --csv HKEYS <key> > /tmp/rediscliout
cp /tmp/rediscliout <dest>
