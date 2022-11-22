CLUSTERHOST1=ccycloud-1.snemeth-netty2.root.hwx.site
CLUSTERHOST2=ccycloud-2.snemeth-netty2.root.hwx.site
CLUSTERHOST3=ccycloud-3.snemeth-netty2.root.hwx.site


ssh $CLUSTERHOST1 "/opt/hadoop/sbin/hadoop-daemon.sh stop datanode && /opt/hadoop/sbin/hadoop-daemon.sh start datanode && echo $?"
ssh $CLUSTERHOST2 "/opt/hadoop/sbin/hadoop-daemon.sh stop datanode && /opt/hadoop/sbin/hadoop-daemon.sh start datanode && echo $?"
ssh $CLUSTERHOST3 "/opt/hadoop/sbin/hadoop-daemon.sh stop datanode && /opt/hadoop/sbin/hadoop-daemon.sh start datanode && echo $?"


# CLUSTERS 2022.11.14
ccycloud.snemeth-nettydriver.root.hwx.site
ccycloud-1.snemeth-netty2.root.hwx.site



scp root@$CLUSTERHOST1:/opt/hadoop/etc/hadoop/yarn-site.xml /tmp/yarn-site1.xml
scp root@$CLUSTERHOST2:/opt/hadoop/etc/hadoop/yarn-site.xml /tmp/yarn-site2.xml
scp root@$CLUSTERHOST3:/opt/hadoop/etc/hadoop/yarn-site.xml /tmp/yarn-site3.xml


Running command yarn application -list -appStates FINISHED 2>/dev/null | grep -oe application_[0-9]*_[0-9]* | sort -r || true