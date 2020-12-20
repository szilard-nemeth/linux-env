CLUSTER_HOST1="root@snemeth-fips2-1.vpc.cloudera.com"
BASEDIR="$LINUX_ENV_REPO/workplace-specific/cloudera/investigations/YARN-10427"

echo "Syncing SLS config files to $CLUSTER_HOST1..."
ssh $CLUSTER_HOST1 "mkdir -p /root/YARN-10427/config" && \
scp -r $BASEDIR/config $CLUSTER_HOST1:/root/YARN-10427/ && \
rsync -avP --exclude="/*/" $BASEDIR/ $CLUSTER_HOST1:/root/YARN-10427 && \
ssh $CLUSTER_HOST1 /root/YARN-10427/start-sls.sh && \
$BASEDIR/save-latest-sls-logs.sh