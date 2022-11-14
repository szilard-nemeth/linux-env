# Manually cleanup large files

ssh ccycloud-1.snemeth-netty.root.hwx.site du -sh /opt/hadoop/logs/\*
ssh ccycloud-2.snemeth-netty.root.hwx.site du -sh /opt/hadoop/logs/\*
ssh ccycloud-3.snemeth-netty.root.hwx.site du -sh /opt/hadoop/logs/\*
ssh ccycloud-4.snemeth-netty.root.hwx.site du -sh /opt/hadoop/logs/\*


ssh ccycloud-1.snemeth-netty.root.hwx.site rm /opt/hadoop/logs/hadoop-systest-nodemanager-ccycloud-1.snemeth-netty.root.hwx.site.out
ssh ccycloud-2.snemeth-netty.root.hwx.site rm /opt/hadoop/logs/hadoop-systest-nodemanager-ccycloud-2.snemeth-netty.root.hwx.site.out
ssh ccycloud-3.snemeth-netty.root.hwx.site rm /opt/hadoop/logs/hadoop-systest-nodemanager-ccycloud-3.snemeth-netty.root.hwx.site.out
ssh ccycloud-4.snemeth-netty.root.hwx.site rm /opt/hadoop/logs/hadoop-systest-nodemanager-ccycloud-4.snemeth-netty.root.hwx.site.out



ssh ccycloud-1.snemeth-netty.root.hwx.site du -sh /tmp/\* | sort -rh
ssh ccycloud-2.snemeth-netty.root.hwx.site du -sh /tmp/\* | sort -rh
ssh ccycloud-3.snemeth-netty.root.hwx.site du -sh /tmp/\* | sort -rh
ssh ccycloud-4.snemeth-netty.root.hwx.site du -sh /tmp/\* | sort -rh



ssh ccycloud-1.snemeth-netty.root.hwx.site df -h
ssh ccycloud-2.snemeth-netty.root.hwx.site df -h
ssh ccycloud-3.snemeth-netty.root.hwx.site df -h
ssh ccycloud-4.snemeth-netty.root.hwx.site df -h


ssh ccycloud-1.snemeth-netty.root.hwx.site cat /opt/hadoop/etc/hadoop/yarn-env.sh
ssh ccycloud-2.snemeth-netty.root.hwx.site cat /opt/hadoop/etc/hadoop/yarn-env.sh
ssh ccycloud-3.snemeth-netty.root.hwx.site cat /opt/hadoop/etc/hadoop/yarn-env.sh
ssh ccycloud-4.snemeth-netty.root.hwx.site cat /opt/hadoop/etc/hadoop/yarn-env.sh


ssh ccycloud-1.snemeth-netty.root.hwx.site grep javax.net.debug /opt/hadoop/etc/hadoop/ -R
ssh ccycloud-2.snemeth-netty.root.hwx.site grep javax.net.debug /opt/hadoop/etc/hadoop/ -R
ssh ccycloud-3.snemeth-netty.root.hwx.site grep javax.net.debug /opt/hadoop/etc/hadoop/ -R
ssh ccycloud-4.snemeth-netty.root.hwx.site grep javax.net.debug /opt/hadoop/etc/hadoop/ -R



ssh ccycloud-1.snemeth-netty.root.hwx.site "/opt/hadoop/sbin/hadoop-daemon.sh stop datanode && /opt/hadoop/sbin/hadoop-daemon.sh start datanode && echo $?"
ssh ccycloud-2.snemeth-netty.root.hwx.site "/opt/hadoop/sbin/hadoop-daemon.sh stop datanode && /opt/hadoop/sbin/hadoop-daemon.sh start datanode && echo $?"
ssh ccycloud-3.snemeth-netty.root.hwx.site "/opt/hadoop/sbin/hadoop-daemon.sh stop datanode && /opt/hadoop/sbin/hadoop-daemon.sh start datanode && echo $?"
ssh ccycloud-4.snemeth-netty.root.hwx.site "/opt/hadoop/sbin/hadoop-daemon.sh stop datanode && /opt/hadoop/sbin/hadoop-daemon.sh start datanode && echo $?"


# CLEANUP CLUSTER
/Users/snemeth/.local/share/virtualenvs/hades-9aTJNEdf/bin/python /Users/snemeth/development/other-repos/gandras/hades/cli.py cleanup-dirs --dir /tmp/ --dir /opt/hadoop/logs --limit 50 




# RESTORE hadoop-mapreduce-client-jobclient-3.4.0-SNAPSHOT-tests.jar on all NM hosts
JOBCL_TESTS_PATH="/opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-client-jobclient-3.4.0-SNAPSHOT-tests.jar"
ssh ccycloud-2.snemeth-netty.root.hwx.site cp /tmp/hades-bkp/hadoop-mapreduce-client-jobclient-3.4.0-SNAPSHOT-tests-1667911122.jar $JOBCL_TESTS_PATH
ssh ccycloud-3.snemeth-netty.root.hwx.site cp /tmp/hades-bkp/hadoop-mapreduce-client-jobclient-3.4.0-SNAPSHOT-tests-1667911124.jar $JOBCL_TESTS_PATH
ssh ccycloud-4.snemeth-netty.root.hwx.site cp /tmp/hades-bkp/hadoop-mapreduce-client-jobclient-3.4.0-SNAPSHOT-tests-1667911121.jar $JOBCL_TESTS_PATH

