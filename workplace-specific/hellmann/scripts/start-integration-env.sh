#!/usr/bin/env bash

set -e

DIR="$(dirname $0)"
cd $DIR

export BUILD_UUID=dev
export DEV_ENV=1

./build-builder-image.sh

./run-in-builder.sh /builder/starts/start-oracle.sh
./run-in-builder.sh /builder/database/init-all.sh

LOCAL_ORACLE=$(hostname -I | cut -d" " -f 1)

#./run-in-builder.sh /builder/starts/start-kafka-feeder.sh $LOCAL_ORACLE
#./run-in-builder.sh /builder/starts/start-dataservice.sh $LOCAL_ORACLE
