##  MANUAL INITIAL SETUP STEPS ON CLUSTER MACHINE - CentOS

### Set up common variables
```
HOST_1="ccycloud-1.snemeth-netty.root.hwx.site"
HOST_2="ccycloud-2.snemeth-netty.root.hwx.site"
HOST_3="ccycloud-3.snemeth-netty.root.hwx.site"
HOST_4="ccycloud-4.snemeth-netty.root.hwx.site"
```

1. Install scp on all hosts:

```
#Generic format: 
ssh ${REMOTE_USER}@$CLOUDERA_HOSTNAME "sudo yum -y install openssh-clients"

ssh systest@$HOST_1 "sudo yum -y install openssh-clients"
ssh systest@$HOST_2 "sudo yum -y install openssh-clients"
ssh systest@$HOST_3 "sudo yum -y install openssh-clients"
ssh systest@$HOST_4 "sudo yum -y install openssh-clients"
```

2. SSH into Host #1:
```
ssh systest@$HOST_1
```

3. Install git:

`sudo yum install -y git`

2. Install Maven:
```
wget -O install-maven.sh https://gist.githubusercontent.com/miroslavtamas/cdca97f2eafdd6c28b844434eaa3b631/raw/c62e4e0210bdc53419ac1fad12aaeb2b4d3f954c/
chmod +x install-maven.sh
./install-maven.sh
mvn
```

2.1 If link does not work, replace it with: `https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.3.9/apache-maven-3.3.9-bin.tar.gz`

3. Install Java
DO NOT USE: `sudo yum install -y java` --> This would install a JRE

Follow this guide: https://developers.redhat.com/blog/2018/12/10/install-java-rhel8
```
sudo yum install java-1.8.0-openjdk-devel
```

4. Set JAVA_HOME

Guide: https://computingforgeeks.com/how-to-set-java_home-on-centos-fedora-rhel/

```
ls -la /etc/alternatives/java

#Should give something like: 
/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.272.b10-1.el7_9.x86_64/jre/bin/java


#Add this to ~/.bashrc
export JAVA_HOME=$(dirname $(dirname $(readlink /etc/alternatives/java)))
echo $JAVA_HOME
```

5. Install other required libraries - Had to manually install protoc + other required libraries with the following commands (in this particular order):
```
sudo yum install -y protobuf-devel
sudo yum install -y gcc gcc-c++ make
sudo yum install -y openssl-devel
sudo yum install -y libgsasl
```

6. Install rsync on all hosts
```
ssh systest@$HOST_1 "sudo yum -y install rsync"
ssh systest@$HOST_2 "sudo yum -y install rsync"
ssh systest@$HOST_3 "sudo yum -y install rsync"
ssh systest@$HOST_4 "sudo yum -y install rsync"
```

---

## Run YARN-cluster-setup
`
cd ~/development/cloudera/YARN-tools/YARN-Cluster-Setup
PATCH_FILE="$HOME/development/my-repos/linux-env/workplace-specific/cloudera/investigations/HADOOP-15327/patches/backup-patch-all-20220711.patch"
CL_SETUP_BRANCH="HADOOP-15327"
`

###Build with trunk
```
./bootstrap-cluster.sh $HOST_1 --dist-type=upstream --cluster-setup-branch=$CL_SETUP_BRANCH
```

###Build with patch
```
./bootstrap-cluster.sh $HOST_1 --dist-type=upstream --patch-file=$PATCH_FILE --cluster-setup-branch=$CL_SETUP_BRANCH
```


###Do not build, just setup
```
./bootstrap-cluster.sh $HOST_1 --dist-type=upstream --patch-file=$PATCH_FILE --cluster-setup-branch=$CL_SETUP_BRANCH --no-build --no-update-hadoop
```

## Restart RM / NMs
```
ssh systest@$HOST_1 '/opt/hadoop/bin/yarn --daemon stop resourcemanager;/opt/hadoop/bin/yarn resourcemanager'
ssh systest@$HOST_2 '/opt/hadoop/bin/yarn --daemon stop nodemanager;/opt/hadoop/bin/yarn nodemanager'
ssh systest@$HOST_3 '/opt/hadoop/bin/yarn --daemon stop nodemanager;/opt/hadoop/bin/yarn nodemanager'
ssh systest@$HOST_4 '/opt/hadoop/bin/yarn --daemon stop nodemanager;/opt/hadoop/bin/yarn nodemanager'
```