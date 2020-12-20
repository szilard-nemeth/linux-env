CLUSTER_HOST1="root@snemeth-fips2-1.vpc.cloudera.com"

echo "Building Hadoop and launching SLS on host: $CLUSTER_HOST1"
mvn-hadoop-cdpd && \
scp ./hadoop-dist/target/hadoop-3.1.1.7.2.7.0-SNAPSHOT.tar.gz $CLUSTER_HOST1: && ./launch-sls.sh