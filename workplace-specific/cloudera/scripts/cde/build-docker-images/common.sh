#!/bin/bash


# docker images | grep "dex-" | awk '{print $3}' | xargs docker rmi -f
# docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
# docker rmi -f docker-private.infra.cloudera.com/cloudera/dex/dex-runtime-python-builder:7.2.16.0-999 docker-private.infra.cloudera.com/cloudera/dex/dex-runtime-python-builder:7.2.18.0-999 docker-private.infra.cloudera.com/cloudera/dex/dex-runtime-python-builder:7.2.15.0-999

# cleanup
# echo "Cleaning up previously built docker images"
# docker images | grep "dex-runtime-python-builder" | awk '{print $3}' | xargs docker rmi -f


DEX_HOME=/Users/snemeth/development/cloudera/cde/dex
BUILD_TYPE=dev
REGISTRY="docker-private.infra.cloudera.com"


echo "Make sure there is no dex-runtime-python-builder docker image"
docker images | grep "\-builder"