#!/bin/bash
#====================================================
###STEPS
# Determine version of CM, git hash
#Version: Cloudera Enterprise 7.1.1 
#(#2064814 built by jenkins on 20200309-0915 git: fee2d5ced359c3f99dfe58b423c1b9cfbaece50f)


#====================================================
#### Run commands on local machine:

# Setup branch: 
#git co -b OPSAPS-54755-fee2d5ced fee2d5ced


#====================================================
#### Run commands on cluster:
function cmhack-init-cluster() {
	##tar CM directories
	tar czhf cm-lib.tar.gz /opt/cloudera/cm/lib/	
}


#====================================================
##Run commands on local machine (In CM dev root dir):
function cmhack-init() {
	CLUSTER="snemeth-secure514-4-1.snemeth-secure514-4.root.hwx.site"
	BASE_GIT_HASH="db13be490c0"

	sshpass -p "password" scp root@$CLUSTER:cm-lib.tar.gz .
	# Run this to see the output of scp
	# scp root@$CLUSTER:cm-lib.tar.gz .
	rmdir hacklib
	mkdir hacklib
	tar -xf cm-lib.tar.gz -C hacklib
	cd hacklib && mv ./opt/cloudera/cm/lib/* . && cd -
}


#====================================================
#Should be executed from CM root dir
function cmhack() {
	
	# FILES=`git status *.java | grep '.java' | grep -v -i test | sed s/modified\://g`
	#TODO this does not recognize changed files well :(
	#FILES=`git status *.java | grep '.java' | grep -v -i test | sed s/modified\://g | sed s/new\ file\://g`

	FILES=$(git diff --name-only $BASE_GIT_HASH..HEAD| grep java | grep -iv test)
	#FILES=`git log --name-only HEAD^..HEAD | grep java | grep -v -i test`
	#FILES="web/src/main/java/com/cloudera/cmf/service/yarn/YarnParams.java  web/src/main/java/com/cloudera/cmf/service/yarn/YarnConfigFileDefinitions.java"

	echo "Found changed / new files: $FILES"

	for FILE in ${FILES}; do
	    echo "***Compiling: $FILE"

	    #web/src/main/java/ --> This must be added as newly compiled java files only available here as a class
	    javac -encoding utf8 -cp "./hacklib/*:web/src/main/java/:libs/common/src/main/java:./libs/common" $FILE
	    if [[ $? -gt 0 ]]; then 
	    	echo "ERROR"
	    	return 1
	    fi
	done

    COMMON_JAR_NAME="common-7.1.1.jar"
	SERVER_JAR_NAME="server-7.1.1.jar"
	
	
	#remove previous hack + DO CLEANUP!
	rm ${SERVER_JAR_NAME}
	rm ${COMMON_JAR_NAME}
	
	#copy original jars to CM root dir
	cp ./hacklib/${SERVER_JAR_NAME} .
	cp ./hacklib/${COMMON_JAR_NAME} .
	

	echo "Zipping all new classes into $SERVER_JAR_NAME"
	cd web/src/main/java/
	zip -i "*.class" -r ../../../../${SERVER_JAR_NAME} com/
	cd -
	
	echo "Zipping all new classes into $COMMON_JAR_NAME"
	cd libs/common/src/main/java
	zip -i "*.class" -r ../../../../../${COMMON_JAR_NAME} com/
	cd -

	echo "Cleaning up generated *.class files"
	find com/ -name '*.class' | xargs rm
	find web/ -name '*.class' | xargs rm
	find libs/ -name '*.class' | xargs rm


	#Rsync to cluster - Assuming using the almighty ycloud :) 
	#If sshpass is not available on Mac:
	#HOMEBREW_NO_AUTO_UPDATE=1 brew install https://raw.githubusercontent.com/kadwanev/bigboybrew/master/Library/Formula/sshpass.rb
	echo "Syncing hack to $CLUSTER:"
	echo "Scping files to cluster $CLUSTER: $SERVER_JAR_NAME, $COMMON_JAR_NAME..."
	sshpass -p "password" rsync ./${SERVER_JAR_NAME} root@${CLUSTER}:/opt/cloudera/cm/lib/
	sshpass -p "password" rsync ./${COMMON_JAR_NAME} root@${CLUSTER}:/opt/cloudera/cm/lib/
	
	echo "Restarting CM server..."
	sshpass -p "password" ssh root@${CLUSTER} "echo \"Restarting cmf server\" && sudo service cloudera-scm-server restart"
}

function cmhack2() {
	#Save script from cluster
	#sshpass -p "password" scp root@$CLUSTER:/opt/cloudera/cm-agent/service/zookeeper/zk-client.sh .
	#cp zk-client.sh agents/cmf/service/zookeeper/zk-client.sh
	echo "Syncing hack to $CLUSTER and restarting CM.."
	sshpass -p "password" rsync ./agents/cmf/service/zookeeper/zk-client.sh root@$CLUSTER:/opt/cloudera/cm-agent/service/zookeeper/zk-client.sh
}

function savePatches() {
	rm ~/Downloads/_inprogress/OPSAPS-54755/format-patch/00*
	git format-patch fee2d5ced35
	mv 00* ~/Downloads/_inprogress/OPSAPS-54755/format-patch/
}