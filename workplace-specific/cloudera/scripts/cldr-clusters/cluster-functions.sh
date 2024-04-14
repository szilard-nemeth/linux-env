#!/usr/bin/env bash

#This method is intented to be used directly on clusters
function rsync_yarn_site_to_workers {
    workers_file=/tmp/workers
    echo "" > ${workers_file}
    for i in `seq 2 20`; do
      WORKER=`echo $HOSTNAME | sed -e "s/-1\./-$i\./g"`
      if [[ ${WORKER} =~ .*-$i\.* ]]; then
        echo "Pinging $WORKER ..."
        if ping ${WORKER} -c 1 &>/dev/null; then
          echo ${WORKER} >> ${workers_file}
          echo "Found. Added worker to ${workers_file}"
        else
          if [[ ! -f ${workers_file} ]]; then
            echo localhost >> ${workers_file}
            echo "Not found. Pseudo cluster"
            break
          fi
        fi
      else
        echo localhost >> ${workers_file}
        echo "Worker nodes not found. Pseudo cluster"
        break
      fi
    done
    
    src_file="/opt/hadoop/etc/hadoop/yarn-site.xml"
    while read HOST; do
        echo "Rsyncing $src_file to host ${HOST}:${src_file}"
        rsync ${src_file} root@${HOST}:${src_file}; 
    done < ${workers_file}
}