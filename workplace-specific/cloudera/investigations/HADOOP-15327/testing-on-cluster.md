# MANUAL INITIAL SETUP STEPS ON CLUSTER MACHINE
0. Install scp with yum
yum -y install openssh-clients
#ssh ${REMOTE_USER}@$CLOUDERA_HOSTNAME "sudo yum -y install openssh-clients"
ssh systest@ccycloud-1.snemeth-netty2.root.hwx.site "sudo yum -y install openssh-clients"
ssh systest@ccycloud-2.snemeth-netty2.root.hwx.site "sudo yum -y install openssh-clients"
ssh systest@ccycloud-3.snemeth-netty2.root.hwx.site "sudo yum -y install openssh-clients"


1. Install git with yum
sudo yum install -y git

2. Install maven: https://gist.githubusercontent.com/miroslavtamas/cdca97f2eafdd6c28b844434eaa3b631/raw/c62e4e0210bdc53419ac1fad12aaeb2b4d3f954c/install-apache-maven-3.3.9.sh
vi install-maven.sh
chmod +x install-maven.sh 
./install-maven.sh 
#paste script from: https://gist.githubusercontent.com/miroslavtamas/cdca97f2eafdd6c28b844434eaa3b631/raw/c62e4e0210bdc53419ac1fad12aaeb2b4d3f954c/, then save
sudo ./install-maven.sh 
mvn


3. Install java with yum
DO NOT USE: sudo yum install -y java --> This would install a JRE

Follow this guide: https://developers.redhat.com/blog/2018/12/10/install-java-rhel8
sudo yum install java-1.8.0-openjdk-devel

4. Set JAVA_HOME
Guide: https://computingforgeeks.com/how-to-set-java_home-on-centos-fedora-rhel/
ls -la /etc/alternatives/java
#Should give something like: /usr/lib/jvm/java-1.8.0-openjdk-1.8.0.272.b10-1.el7_9.x86_64/jre/bin/java

#Add this to ~/.bashrc
export JAVA_HOME=$(dirname $(dirname $(readlink /etc/alternatives/java)))
echo $JAVA_HOME

5. Install other required libraries - Had to manually install protoc + other required libraries with the following commands (in this particular order):
sudo yum install -y protobuf-devel
sudo yum install -y gcc gcc-c++ make
sudo yum install -y openssl-devel
sudo yum install -y libgsasl

6. Install rsync
sudo yum install -y rsync
ssh systest@ccycloud-1.snemeth-netty2.root.hwx.site "sudo yum -y install rsync"
ssh systest@ccycloud-2.snemeth-netty2.root.hwx.site "sudo yum -y install rsync"
ssh systest@ccycloud-3.snemeth-netty2.root.hwx.site "sudo yum -y install rsync"



# Run YARN-cluster-setup
cd ~/development/cloudera/YARN-tools/YARN-Cluster-Setup

#WITH BUILD
./bootstrap-cluster.sh ccycloud-1.snemeth-netty2.root.hwx.site --dist-type=upstream --patch-file=~/googledrive/development_drive/_upstream/HADOOP-15327/patches/official-patches/HADOOP-15327.005.patch --cluster-setup-branch=HADOOP-15327


#NO BUILD
./bootstrap-cluster.sh ccycloud-1.snemeth-netty2.root.hwx.site --dist-type=upstream --patch-file=~/googledrive/development_drive/_upstream/HADOOP-15327/patches/official-patches/HADOOP-15327.005.patch --cluster-setup-branch=HADOOP-15327 --no-build --no-update-hadoop