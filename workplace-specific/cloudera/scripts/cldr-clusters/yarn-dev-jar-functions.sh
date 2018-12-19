
#LOOK_FOR="codehaus/xfire/spring"

function find_names_in_jars() {
    PATH="$1"
    JAR_FILE="$2"
    LOOK_FOR="$3"
    
    for i in `find . -name "*$JAR_FILE*jar"`
    do
      echo "Looking in $i ..."
      jar tvf $i | grep ${LOOK_FOR} > /dev/null
      if [[ $? == 0 ]]
      then
        echo "==> Found \"$LOOK_FOR\" in $i"
      fi
    done
}

function grep_in_nodemanager_jar() {
    find /opt/hadoop/share/hadoop/yarn/ -iname 'hadoop-yarn-server*nodemanager*' ! -iname "*test*.jar" ! -iname "*sources*jar" -printf "unzip -c %p | grep -q '$1' && echo %p\n"
    find /opt/hadoop/share/hadoop/yarn/ -iname 'hadoop-yarn-server*nodemanager*' ! -iname "*test*.jar" ! -iname "*sources*jar" -printf "unzip -c %p | grep 'Calling pluginManager' && echo %p\n" | sh
}


function grep_in_code() {
    SEARCH_FOR="$1"

    FIND_RESULTS=$(find /opt/hadoop/share/hadoop/yarn/ -iname 'hadoop-yarn-server*nodemanager*' ! -iname "*test*.jar" ! -iname "*sources*jar")
    echo ${FIND_RESULTS} | grep -E '[ "]' > /dev/null && echo "Find has 2 or more result lines: $FIND_RESULTS" && exit 1
    JAR="$FIND_RESULTS"
    CLASSNAME=$(jar tf $JAR | grep 'org.apache.hadoop.yarn.server.nodemanager.NodeManager.class')
    
    cd /tmp
    jar xf ${JAR} ${CLASSNAME}
    javap -c ${CLASSNAME}  | grep -i "$SEARCH_FOR"
    cd -
}

function grep_in_code_from_given_jar() {
    SEARCH_FOR="$1"
    
     JAR="/opt/hadoop/share/hadoop/yarn/hadoop-yarn-server-nodemanager-3.3.0-SNAPSHOT.jar"
#    JAR="/opt/hadoop/share/hadoop/yarn/hadoop-yarn-server-nodemanager-3.0.0-cdh6.x-SNAPSHOT.jar"
    CLASSNAME=$(jar tf $JAR | grep 'org.apache.hadoop.yarn.server.nodemanager.NodeManager.class')
    
    cd /tmp
    jar xf ${JAR} ${CLASSNAME}
    javap -c ${CLASSNAME}  | grep -i "$SEARCH_FOR"
    cd -
}
