#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
. $DIR/common.sh

if [ -z "$DEX_HOME" ]; then
  echo "DEX_HOME is unset. Please set and export it!" 1>&2
  exit 1
fi

echo "================================================================================================"
echo "Building PC 7.2.18"
VERSION=7.2.18.0-999
# SPARK_VERSION=2.4.8
# export SPARK_VERSION

cd $DEX_HOME

export PYTHON_VERSION_FOR_BUILDER=python38
bash -c "DEX_HOME=${DEX_HOME} ./cloudera/exec ./export.sh"
bash -c "DEX_HOME=${DEX_HOME} FORM_FACTOR=pc CDP_PLATFORM=7.2.18 ./cloudera/exec make platform-based-excluding-spark2-images REGISTRY=${REGISTRY} VERSION=${VERSION} BUILD_TYPE=${BUILD_TYPE}"


# cdhver=$(grep "CDH_VERSION.*=" ./re_vars_cdh_7.2.18.env | cut -d '=' -f2)
# echo "Pushing image"
# SRC_IMG="docker-private.infra.cloudera.com/cloudera/dex/dex-runtime-python-builder-$cdhver:7.2.18.0-999"
# TARGET_IMG="docker-registry.infra.cloudera.com/snemeth/dex-runtime-python-builder-$cdhver:7.2.18.0-999"

# set -x
# docker tag $SRC_IMG $TARGET_IMG
# docker push $TARGET_IMG
# set +x
# echo "================================================================================================"