echo "================================================================================================"
echo "Building $FORM_FACTOR $CDP_PLATFORM"

cd $DEX_HOME

bash -c "DEX_HOME=${DEX_HOME} ./cloudera/exec ./export.sh"
bash -c "DEX_HOME=${DEX_HOME} ./cloudera/exec make printenv REGISTRY=${REGISTRY} VERSION=${VERSION} BUILD_TYPE=${BUILD_TYPE}"
bash -c "DEX_HOME=${DEX_HOME} ./cloudera/exec make clean-docker-metadata REGISTRY=${REGISTRY} VERSION=${VERSION} BUILD_TYPE=${BUILD_TYPE}"
# bash -c "DEX_HOME=${DEX_HOME} ENABLE_MULTI_ARCH_BUILD=false FORM_FACTOR=$FORM_FACTOR CDP_PLATFORM=$CDP_PLATFORM ./cloudera/exec make platform-based-docker-images REGISTRY=${REGISTRY} VERSION=${VERSION} BUILD_TYPE=${BUILD_TYPE}"
# bash -c "DEX_HOME=${DEX_HOME} ENABLE_MULTI_ARCH_BUILD=false FORM_FACTOR=$FORM_FACTOR CDP_PLATFORM=$CDP_PLATFORM ./cloudera/exec make dex-spark3-runtime-v2 dex-spark3-runtime-gpu-v2 dex-livy-runtime-spark3-v2 dex-livy-runtime-spark3-gpu-v2 dex-runtime-python-builder-v2 REGISTRY=${REGISTRY} VERSION=${VERSION} BUILD_TYPE=${BUILD_TYPE}"


# Build list of Docker images manually
cd $DEX_HOME/docker
set -e
echo "***Building docker images"
bash -c "DEX_HOME=${DEX_HOME} ENABLE_MULTI_ARCH_BUILD=false FORM_FACTOR=$FORM_FACTOR CDP_PLATFORM=$CDP_PLATFORM make dex-spark3-runtime-v2 dex-spark3-runtime-gpu-v2 dex-livy-runtime-spark3-v2 dex-livy-runtime-spark3-gpu-v2 dex-runtime-python-builder-v2 REGISTRY=${REGISTRY} VERSION=${VERSION} BUILD_TYPE=${BUILD_TYPE}"

echo "Built docker images: "
docker images | grep $CDP_PLATFORM | grep cloudera/dex | grep "cde-"


# cdhver=$(grep "CDH_VERSION.*=" ./re_vars_cdh_7.1.8.env | cut -d '=' -f2)
# echo "Pushing image"
# SRC_IMG="docker-private.infra.cloudera.com/cloudera/dex/dex-runtime-python-builder-$cdhver:7.1.8.0-999"
# TARGET_IMG="docker-registry.infra.cloudera.com/snemeth/dex-runtime-python-builder-$cdhver:7.1.8.0-999"
# set -x
# docker tag $SRC_IMG $TARGET_IMG
# docker push $TARGET_IMG
# set +x
# echo "================================================================================================"
