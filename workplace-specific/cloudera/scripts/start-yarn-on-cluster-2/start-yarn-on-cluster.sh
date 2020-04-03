#!/usr/bin/env bash

#set -x
usage() { echo "Usage: $0 -h [HOSTNAME] -t [TESTCASEDIR] -s" 1>&2; exit 1; }

function run_yarn_testcases() {
    local testcase_dir=$1
    local config_script="$2"
    CLDR_YARN_CFG_DIR="/home/systest/yarnconfigs"
    
    for d in ${testcase_dir}/*; do
        if [[ -d ${d} ]]; then
            echo "Searching for config files [yarn-site*.xml, node-resources*.xml, resource-types*.xml] in $d"
            CONFIG_FILES=$(find ${d} -type f \( -iname "node-resources*xml" -o -iname "resource-types*xml" \))

            echo "Config files found: $CONFIG_FILES in $d"
            rm ${config_script}
            touch ${config_script}
            added_to_script=0
            for f in ${CONFIG_FILES}; do
                echo "***file: $f"
                #copy node-resources.xml to all workers
                if [[ ${f} =~ node-resources.*$ ]]; then
                    for i in `seq 2 101`;
                    do
                      WORKER=`echo ${CLOUDERA_HOSTNAME} | sed -e "s/-1\./-$i\./g"`
                      if [[ ${WORKER} =~ .*-$i\.* ]]
                      then
                        echo Pinging ${WORKER} ...
                        if ping ${WORKER}.cloudera.com -c 1 &>/dev/null
                        then
                          SCP_FILEPATH=${CLDR_YARN_CFG_DIR}/$(basename ${d})/$(basename ${f})
                          SCP_FULL_PATH=${WORKER}:${SCP_FILEPATH}
                          ssh ${WORKER} "mkdir -p $SCP_FILEPATH"
                          echo "Copying file $f to worker host: $SCP_FULL_PATH" 
                          scp ${f} ${SCP_FULL_PATH}
                          if [[ ${added_to_script} -eq 0 ]]; then
                            echo "cp $CLDR_YARN_CFG_DIR/$(basename ${d})/$(basename ${f}) /opt/hadoop/etc/hadoop/" >> ${config_script}
                          fi
                        fi
                      fi
                    done
                else
                    SCP_FILEPATH=${CLDR_YARN_CFG_DIR}/$(basename ${d})/$(basename ${f})
                    SCP_FULL_PATH=${CLOUDERA_HOSTNAME}:${SCP_FILEPATH}
                    ssh ${CLOUDERA_HOSTNAME} "mkdir -p $SCP_FILEPATH"
                    echo "Copying file $f to main host: $SCP_FULL_PATH" 
                    scp ${f} ${SCP_FULL_PATH}
                    echo "cp $CLDR_YARN_CFG_DIR/$(basename ${d})/$(basename ${f}) /opt/hadoop/etc/hadoop/" >> ${config_script}
                fi
            done
            echo -e "YARN setup script generated to $config_script, listing contents:\n"
            cat ${CONFIG_SCRIPT}
        fi
    done
}

POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"
    case ${key} in
        -h|--hostname)
        CLOUDERA_HOSTNAME="$2"
        shift # past argument
        shift # past value
        ;;
        -t|--testcase-dir)
        TESTCASE_DIR="$2"
        shift # past argument
        shift # past value
        ;;
        -s|--skip-build)
        SKIP_BUILD="yes"
        shift # past argument
        ;;
        *)    # unknown option
        POSITIONAL+=("$1") # save it in an array for later
        shift # past argument
        ;;
    esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

echo CLOUDERA HOSTNAME  = "${CLOUDERA_HOSTNAME}"
echo TESTCASE DIR     = "${TESTCASE_DIR}"
echo SKIP BUILD    = "${SKIP_BUILD}"

if [ -z "${CLOUDERA_HOSTNAME}" ]; then
    usage
fi

if [ -z "${SKIP_BUILD}" ]; then
    echo "Bulding upstream YARN..."
    #mvn clean package -Pdist -DskipTests -Dmaven.javadoc.skip=true && scp hadoop-dist/target/hadoop-${MY_HADOOP_VERSION}.tar.gz systest@${CLOUDERA_HOSTNAME}:~
fi

if [ ! -z "${TESTCASE_DIR}" ] && [ ! -d "${TESTCASE_DIR}" ]; then
    echo "Testcase directory "${TESTCASE_DIR}" does not exist."
    exit 1
fi

pushd ~/development/apache/hadoop;
MY_HADOOP_VERSION=$(mvn org.apache.maven.plugins:maven-help-plugin:2.1.1:evaluate \
    -Dexpression=project.version 2>/dev/null |grep -Ev '(^\[|Download\w+:)')
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


if [ ! -z "${TESTCASE_DIR}" ]; then
    CONFIG_SCRIPT=/tmp/yarn-config-script.sh
    run_yarn_testcases ${TESTCASE_DIR} ${CONFIG_SCRIPT}
  
    #ssh systest@$CLOUDERA_HOSTNAME "MY_HADOOP_VERSION=$MY_HADOOP_VERSION YARN_CONFIG_SCRIPT=$CONFIG_SCRIPT" 'bash -s' < "$DIR/start-yarn-on-cluster-remote.sh"
else
    echo "Running start-yarn-on-cluster-remote.sh on $CLOUDERA_HOSTNAME...";
    #ssh systest@$CLOUDERA_HOSTNAME "MY_HADOOP_VERSION=$MY_HADOOP_VERSION" 'bash -s' < "$DIR/start-yarn-on-cluster-remote.sh"
fi