#!/bin/bash


CLUSTER="snemeth-514-secure6-1.snemeth-514-secure6.root.hwx.site"
###STEPS
# Determine version of CM, git hash
#Version: Cloudera Enterprise 7.1.1 
#(#2064814 built by jenkins on 20200309-0915 git: fee2d5ced359c3f99dfe58b423c1b9cfbaece50f)


#### Run commands locally:
# Setup branch: 
#git co -b OPSAPS-54755-fee2d5ced fee2d5ced


#### Run commands on cluster:
#tar CM directories: 
#tar czhf cm-lib.tar.gz /opt/cloudera/cm/lib/

#Run commands locally (In CM dev root dir):
#scp root@$CLUSTER:cm-lib.tar.gz .
#mkdir hacklib 
#tar -xf cm-lib.tar.gz -C hacklib
#cd hacklib && mv ./opt/cloudera/cm/lib/* . && cd -

# /Users/szilardnemeth/.m2/repository//com/cloudera/cmon/firehose/6.x.0/firehose-6.x.0.jar

#Should be executed from CM root dir
function cmhack() {
	
	# FILES=`git status *.java | grep '.java' | grep -v -i test | sed s/modified\://g`
	#TODO this does not recognize changed files well :(
	#FILES=`git status *.java | grep '.java' | grep -v -i test | sed s/modified\://g | sed s/new\ file\://g`

	FILES=$(git diff --name-only HEAD| grep java)
	#FILES=`git log --name-only HEAD^..HEAD | grep java | grep -v -i test`
	#FILES="web/src/main/java/com/cloudera/cmf/service/yarn/YarnParams.java  web/src/main/java/com/cloudera/cmf/service/yarn/YarnConfigFileDefinitions.java"

	echo "Found changed / new files: $FILES"

	for FILE in $FILES; do
	    echo "***Compiling: $FILE"

	    #web/src/main/java/ --> This must be added as newly compiled java files only available here as a class
	    javac -encoding utf8 -cp "./hacklib/*:web/src/main/java/:libs/common/src/main/java:./libs/common" $FILE
	    if [ $? -gt 0 ]; then 
	    	echo "ERROR"
	    	return 1
	    fi
	done

	JAR_NAME="server-7.1.1.jar"
	#remove previous hack + DO CLEANUP!
	rm $JAR_NAME
	
	#copy original jar to CM root dir
	cp ./hacklib/$JAR_NAME .	

	#Zip all new classes into the jar
	cd web/src/main/java/
	zip -i "*.class" -r ../../../../$JAR_NAME com/
	cd -

	#DO CLEANUP
	find com/ -name '*.class' | xargs rm
	find web/ -name '*.class' | xargs rm


	#Rsync to cluster - Assuming using the almighty ycloud :) 
	#If sshpass is not available on Mac:
	#HOMEBREW_NO_AUTO_UPDATE=1 brew install https://raw.githubusercontent.com/kadwanev/bigboybrew/master/Library/Formula/sshpass.rb
	echo "Syncing hack to $CLUSTER and restarting CM.."
	sshpass -p "password" rsync ./$JAR_NAME root@$CLUSTER:/opt/cloudera/cm/lib/

	sshpass -p "password" ssh root@$CLUSTER "echo \"Restarting cmf server\" && sudo service cloudera-scm-server restart"
}

function cmhack2() {
	#Save script from cluster
	#sshpass -p "password" scp root@$CLUSTER:/opt/cloudera/cm-agent/service/zookeeper/zk2.sh .
	#cp zk2.sh agents/cmf/service/zookeeper/zk2.sh
	sshpass -p "password" rsync ./agents/cmf/service/zookeeper/zk2.sh root@$CLUSTER:/opt/cloudera/cm-agent/service/zookeeper/zk2.sh
}