CLUSTER_HOST1="root@snemeth-fips2-1.vpc.cloudera.com"
##Build & upload to cluster + start SLS run
mvn-hadoop-cdpd && \
scp ./hadoop-dist/target/hadoop-3.1.1.7.2.7.0-SNAPSHOT.tar.gz $CLUSTER_HOST1: && ./launch-sls.sh