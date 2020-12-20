CLUSTER_HOST1="root@snemeth-fips2-1.vpc.cloudera.com"
ssh $CLUSTER_HOST1 "mkdir -p /root/YARN-10427/config" && \
scp -r ~/Downloads/YARN-10427/config $CLUSTER_HOST1:/root/YARN-10427/ && \
rsync -avP --exclude="/*/" ~/Downloads/YARN-10427/ $CLUSTER_HOST1:/root/YARN-10427 && \
ssh $CLUSTER_HOST1 /root/YARN-10427/start-sls.sh