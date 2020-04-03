#!/bin/bash

###STEPS
#1. Determine version of CM, git hash

##Run on cluster
#2. tar CM directories: tar czhf cm-lib.tar.gz /opt/cloudera/cm/lib/
#3. scp tar.gz

#Run locally
#scp systest@quasar-canxrv-1.vpc.cloudera.com:cm-lib.tar.gz .
#mkdir hacklib 
#tar -xf cm-lib.tar.gz -C hacklib
#cd hacklib && mv ./opt/cloudera/cm/lib/* . && cd -

# /Users/szilardnemeth/.m2/repository//com/cloudera/cmon/firehose/6.x.0/firehose-6.x.0.jar

#Should be executed from CM root dir

function cmhack() {
	FILES=`git status *.java | grep '.java' | grep -v -i test | sed s/modified\://g`
	#FILES=`git log --name-only HEAD^..HEAD | grep java | grep -v -i test`
	#FILES="web/src/main/java/com/cloudera/cmf/service/yarn/YarnParams.java  web/src/main/java/com/cloudera/cmf/service/yarn/YarnConfigFileDefinitions.java"

	echo ${FILES}

	for FILE in ${FILES}; do
	    echo ${FILE}
	    #web/src/main/java/ --> This must be added as newly compiled java files only available here as a class
	    javac -encoding utf8 -cp "./hacklib/*:web/src/main/java/" ${FILE}
	    if [ $? -gt 0 ]; then
	    	echo "ERROR!!!"
	    fi
	done

	#remove previous hack!
	rm firehose-6.3.0.jar

	#original jar
	cp ./hacklib/firehose-6.3.0.jar .

	cd daemons/firehose/src/main/java

	#Zip all new classes into the jar
	zip -i "*.class" -r ../../../../../firehose-6.3.0.jar com/

	#Cleanup! (optional)
	find com/ -name '*.class' | xargs rm
	cd -

	rsync ./firehose-6.3.0.jar quasar-canxrv-1.vpc.cloudera.com:/opt/cloudera/cm/lib/
}