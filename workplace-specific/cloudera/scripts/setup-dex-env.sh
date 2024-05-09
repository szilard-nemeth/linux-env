#!/usr/bin/env bash

echo "Setting up DEX env..."

source /Users/snemeth/development/cloudera/hackathon2022/dexter/dexter-setup.sh

############## VARS ##############
DOCKER_ROOT_CLOUDERA="docker-registry.infra.cloudera.com"
DEX_DOCKER_IMAGES_GENERATED_FILE="$DEX_DEV_ROOT/cloudera/docker_images.generated.yaml"

# dummy workplace will resolve to mow-priv as: 
# s-console.cdp-priv.mow-dev.cloudera.com redirects to mow-priv
DUMMY_CSI_WORKSPACE="s"
PRIVATE_STACK_CSI_WORKSPACE=$(whoami)


NAMESPACE_PRIVATE_STACK="snemeth-dex"
NAMESPACE_MOWPRIV="dex"

DEX_CFG_GREP_IN_LOGS=0
DEX_CFG_GREP_FOR="\*\*"

############## VARS ##############

# asdf setup
#. /usr/local/opt/asdf/libexec/asdf.sh
. /opt/homebrew/opt/asdf/libexec/asdf.sh

# aws-okta
#autoload -U +X bashcompinit && bashcompinit
#autoload -U +X compinit && compinit
#source "${HOME}/.bashrc_aws-okta"
# ~aws-okta


# saml2aws auto-completion
eval "$(saml2aws --completion-script-zsh)"



# https://github.infra.cloudera.com/SRE/cloud-users/tree/master/scripts/cloudera-cloud-users
source "$(brew --prefix)/lib/cloudera-cloud-users.sh"
autoload -U +X bashcompinit && bashcompinit
autoload -U +X compinit && compinit


# https://github.infra.cloudera.com/pages/SRE/docs/AWS/usage_command-line/#install-and-configure
export MOW_AUTH_TOOL=none

complete -C '/usr/local/bin/aws_completer' aws


# DEX Variables, Add them to path
export CSI_HOME="$HOME/development/cloudera/cde/cloud-services-infra/"
export DEX_DEV_TOOLS="$DEX_DEV_ROOT/dev-tools"
export PATH=$PATH:$CSI_HOME/bin:$CSI_HOME/moonlander:$DEX_DEV_TOOLS:$DEX_DEV_ROOT/build


# Moonlander / Private stacks: https://github.infra.cloudera.com/CDH/dex/wiki/Private-Stacks-Moonlander
source $DEX_DEV_ROOT/lib/tools/dexk.sh


#################################### DEX functions ####################################
function dex-export-protoc25 {
  asdf uninstall protoc && asdf uninstall maven && cp /usr/local/bin/protoc_old /usr/local/bin/protoc
  # export PATH=<path-to-protobuf2.5>/protobuf-2.5.0/install/bin:$PATH
}



#Go setup
function dex-export-gopath {
	export GOPATH=$(go env GOPATH) # /Users/snemeth/.asdf/installs/golang/1.20.7/go
	export GOBIN=$GOPATH/bin
	export PATH=$PATH:$GOPATH/bin
	export GOOS=darwin
}


# https://github.infra.cloudera.com/CDH/dex-utils/tree/master/cdp-token-chrome
function cst {
  local CHROME_PROFILE="Default"
	env=dev
	if [[ $# > 0 ]]
	then
		env=$1
	fi
	case $env in
		(dev) profile="$CHROME_PROFILE"  ;;
		(int) profile="$CHROME_PROFILE"  ;;
		(stage) profile="$CHROME_PROFILE"  ;;
		(prod) profile="$CHROME_PROFILE"  ;;
	esac
	CST=$(~/.dex/bin/cdp-token-chrome --profile $profile)
	if [[ -z $CST ]]
	then
		echo "Failed to find cdp-session-token cookie in $profile"
	else
		export CST
	fi
}

function dex-default-env {
  CLUSTER_ID="${CLUSTER_ID:-cluster-changeme}"
  VIRTUAL_CLUSTER_NAME="${VIRTUAL_CLUSTER_NAME:-${USER}-SysTest}"
  MOW_ENV="${MOW_ENV:-priv}"
  CSI_WORKSPACE="${CSI_WORKSPACE:-snemeth}"
  #DEXW_AUTH="${DEXW_AUTH:-cdpcurl}"
  DEXW_AUTH="${DEXW_AUTH:-cst}"
  #CDPCURL_BIN="${CDPCURL_BIN:-${HOME}/Development/cloudera/cdpcurl/cdpcurlenv/bin/cdpcurl}"
}


###################################################################### DEX RUNTIME ######################################################################
# The following Runtime aliases are based on: https://github.infra.cloudera.com/CDH/dex/blob/develop/docs/developer-workflow-runtime-api.md

function dex-export-common {
  export JIRA_NUM=$(git rev-parse --abbrev-ref HEAD)
  export VERSION=1.19.0-dev
  export INSTANCE_NAME=snemeth-test
  export REGISTRY_NAMESPACE=${USER}
  export DOCKER_NAMESPACE_ROOT="$DOCKER_ROOT_CLOUDERA/$REGISTRY_NAMESPACE"
  # should be simply 'dex' if using main mow-dev CDE service
  export INGRESS_PATH=dex
}

function dex-export-runtime-build-env {
  # https://superuser.com/a/556006/640183
  read "CLUSTER_ID?Enter service id [cluster-6lznwhlx]: "
  read "DEX_APP_NS?Enter VC id [dex-app-25fcmch8]: "
  read "PROVISIONER_ID?Enter provisioner ID [liftie-cwzvgrxp]: "
  read "CLUSTER_URL?Enter cluster URL [https://console.cdp-priv.mow-dev.cloudera.com/dex]: "

  local curr_date=`date +%F-%H%M%S`
  echo "$curr_date PROVISIONER_ID: $PROVISIONER_ID" >> ~/.cde/clusters-provisioned
  echo "$curr_date CLUSTER_ID: $CLUSTER_ID" >> ~/.cde/clusters-provisioned
  echo "$curr_date DEX_APP_NS: $DEX_APP_NS" >> ~/.cde/clusters-provisioned
  echo "$curr_date CLUSTER_URL: $CLUSTER_URL" >> ~/.cde/clusters-provisioned

	dex-export-common

	echo "##############################################"
	echo "# JIRA_NUM=$JIRA_NUM (used by build)"
	echo "# VERSION=$VERSION (used by build)"
	echo "# REGISTRY_NAMESPACE=$REGISTRY_NAMESPACE (used by build)"
	echo "# INSTANCE_NAME=$INSTANCE_NAME (used by deploy)"
	echo "# CLUSTER_ID=$CLUSTER_ID (used by deploy)"
  echo "# DEX_APP_NS (VC ID)=$DEX_APP_NS (used by deploy)"
	echo "# INGRESS_PATH=$INGRESS_PATH (used by deploy)"
	echo "##############################################"

  dex-parse-latest-cluster-vars
}

function dex-parse-latest-cluster-vars {
  PROVISIONER_ID=$(grep PROVISIONER_ID ~/.cde/clusters-provisioned | tail -n 1 | cut -d : -f 2 | awk '{$1=$1};1')
  CLUSTER_ID=$(grep CLUSTER_ID ~/.cde/clusters-provisioned | tail -n 1 | cut -d : -f 2 | awk '{$1=$1};1')
  DEX_APP_NS=$(grep DEX_APP_NS ~/.cde/clusters-provisioned | tail -n 1 | cut -d : -f 2 | awk '{$1=$1};1')
  CLUSTER_URL=$(grep CLUSTER_URL ~/.cde/clusters-provisioned | tail -n 1 | cut -d : -f 2- | awk '{$1=$1};1')


  echo "##################PARSED DATA FROM FILE: $HOME/.cde/clusters-provisioned ##################"
  echo "# PROVISIONER_ID=$PROVISIONER_ID"
  echo "# CLUSTER_ID=$CLUSTER_ID"
  echo "# DEX_APP_NS=$DEX_APP_NS"
  echo "# CLUSTER_URL=$CLUSTER_URL"
  echo "#########################################################"

  set -x
  dex-export-common
  export CLUSTER_ID
  export DEX_APP_NS
  export CLUSTER_URL
  set +x

  # TODO validate if CLUSTER_ID starts with cluster-
  # TODO validate if DEX_APP_NS starts with dex-app-
}

function dex-pvc-export-runtime-build-env {
  export JIRA_NUM=$(git rev-parse --abbrev-ref HEAD)
  export VERSION=1.18.2
  export REGISTRY_NAMESPACE=${USER}


  echo "##############################################"
  echo "# JIRA_NUM=$JIRA_NUM"
  echo "# VERSION=$VERSION"
  echo "# REGISTRY_NAMESPACE=$REGISTRY_NAMESPACE"
  echo "##############################################"
}


function _dex-build {
  if [ -z ${REGISTRY_NAMESPACE+x} ]; then
			echo "REGISTRY_NAMESPACE is not set. Call 'dex-export-runtime-build-env' or 'dex-parse-latest-cluster-vars' first";
			return 1
		else
			echo "REGISTRY_NAMESPACE set to '$REGISTRY_NAMESPACE'";
	fi


    # Should call manually: dex-export-runtime-build-env
  	cd $DEX_DEV_ROOT/docker
    make $service_to_build

    if [ "$?" -ne 0 ]; then
      echo "Failed to build service: $service_to_build"
      cd -
      return 1
    fi

    cd -
}

function _dex-tag-and-push-image {
  echo "Listing images for service $service_to_build..."
  docker images | grep $service_to_build | grep $VERSION

  image_to_tag=$DOCKER_NAMESPACE_ROOT/$service_to_build:${VERSION}
  docker image inspect $image_to_tag >/dev/null 2>&1

  if [ "$?" -ne 0 ]; then
      echo "Docker image does not exist: $image_to_tag"
      echo "All docker images found for service: "
      docker images | grep $service_to_build

      
      
      echo "Trying to be smart and grep for built Airflow image name from $DEX_DOCKER_IMAGES_GENERATED_FILE"
      # sed 1: remove all leading whitespaces
      # sed 2: remove all trailing } characters
      found_service_img=$(grep $service_to_build $DEX_DOCKER_IMAGES_GENERATED_FILE | cut -d':' -f2 | tr -s ' ' | sed -e 's/^[ \t]*//' | sed 's/}*$//')

      if [[ -z $found_service_img ]]; then
        echo "Couldn't find Docker image for service $service_to_build in file: $DEX_DOCKER_IMAGES_GENERATED_FILE"
        return 1
      else
        service_to_build=$(echo $found_service_img | grep -o "$service_to_build.*")
        return 0
      fi
  fi

  set -x
  docker tag $image_to_tag $image_to_tag-${JIRA_NUM}
  docker push $image_to_tag-${JIRA_NUM}
  set +x
}

function _dex-increase-docker-tag-counter {
  set -x
  if [[ -z $VERSION ]]; then
    echo "VERSION must be set"
    return 1
  fi

  if [[ -z $REGISTRY_NAMESPACE ]]; then
    echo "REGISTRY_NAMESPACE must be set"
    return 1
  fi


  if [[ -z $JIRA_NUM ]]; then
    echo "JIRA_NUM must be set"
    return 1
  fi

  counter=$(_get_latest_counter_for_image | tail -1)
  echo "Current tag counter for Docker image '${arr[1]}': $counter"
  let "counter++"
  echo "Increased tag counter for Docker image '${arr[1]}': $counter"

  new_tag="${VERSION}-${JIRA_NUM}-iteration-$counter"


  image_to_tag=$DOCKER_NAMESPACE_ROOT/$service_to_build:${VERSION}
  image_tagged=$DOCKER_NAMESPACE_ROOT/$service_to_build:$new_tag

  # TODO this wrongly assumes that '$DOCKER_ROOT_CLOUDERA/${REGISTRY_NAMESPACE}/$service_to_build' image exists
  docker tag $image_to_tag $image_tagged
  docker push $image_tagged

  # TODO Filter images with docker images itself - https://stackoverflow.com/questions/24659300/how-to-use-docker-images-filter
  docker images | grep $image_tagged

  echo "Use this image to replace service on cluster:"
  echo $image_tagged
}

function _get_latest_counter_for_image {
  #docker-registry.infra.cloudera.com/snemeth/dex-runtime-api-server 1.18.0-dev-DEX-7712 06bb27949544 2 hours ago 646MB
  arr=($(docker images | grep $service_to_build | grep $JIRA_NUM-iteration- | grep $VERSION-$JIRA_NUM | head -n 1 | tr -s ' '))

  if [[ ${#arr[@]} == 0 ]];then
    echo "Counter not found for Docker image '${arr[1]}'. Setting counter to 0"
    # counter=0
    echo "0"
  else
    unset counter
    d_tag=${arr[2]}
    [[ $d_tag =~ '^[0-9A-Za-z_\.\-]+-iteration-([0-9]+)$' ]] && counter=$match[1]

    if [[ -z $counter ]]; then
      echo "Counter not found for Docker image '${arr[1]}'"
      #counter=0
      echo "0"
    else
      echo "$counter"
    fi
  fi
}

function dex-build-runtime {
  service_to_build="dex-runtime-api-server"

  _dex-build
  if [ "$?" -ne 0 ]; then
    echo "Build unsuccessful!"
    return 1
  fi
  

  _dex-tag-and-push-image
  if [ "$?" -ne 0 ]; then
    echo "Tag and push Docker image unsuccessful!"
    return 2
  fi

  _dex-increase-docker-tag-counter
}

function dex-build-airflow {
  service_to_build="dex-airflow"

  _dex-build
  if [ "$?" -ne 0 ]; then
    echo "Build unsuccessful!"
    return 1
  fi
  
  _dex-tag-and-push-image
  if [ "$?" -ne 0 ]; then
    echo "Tag and push Docker image unsuccessful!"
    return 2
  fi

  _dex-increase-docker-tag-counter
}

function dex-build-cp {
  service_to_build="dex-cp"
  _dex-build
 
 if [ "$?" -ne 0 ]; then
    echo "Build unsuccessful!"
    return 1
  fi
  
  _dex-tag-and-push-image
  if [ "$?" -ne 0 ]; then
    echo "Tag and push Docker image unsuccessful!"
    return 2
  fi

  _dex-increase-docker-tag-counter
}

function dex-deploy-new-vc-runtime-mowdev {
  _dex-deploy-runtime-dev-auto "mow-dev"
}

function dex-deploy-new-vc-runtime-mowpriv {
  _dex-deploy-runtime-dev-auto "mow-priv"
}

function _dex-deploy-runtime-dev-auto {
  local mow_env="$1"
  # Setting the pull policy to always means you can push multiple iterations to the same Docker tag when testing.

  if [[ -z $CLUSTER_ID ]]; then
        echo "CLUSTER_ID must be set" >&2
        return 1
  fi

  if [[ -z $INGRESS_PATH ]]; then
        echo "INGRESS_PATH must be set" >&2
        return 1
  fi

  if [[ -z $INSTANCE_NAME ]]; then
        echo "INSTANCE_NAME must be set" >&2
        return 1
  fi

  if [[ "$mow_env" == "mow-dev" ]]; then
      local dex_deploy_url="https://console.dps.mow-dev.cloudera.com/${INGRESS_PATH}/api/v1/cluster/${CLUSTER_ID}/instance"
  elif [[ "$mow_env" == "mow-priv" ]]; then
      local dex_deploy_url="https://console.cdp-priv.mow-dev.cloudera.com/${INGRESS_PATH}/api/v1/cluster/${CLUSTER_ID}/instance"
  fi

  echo "Using DEX deploy URL: $dex_deploy_url"

  cst; curl -H 'Content-Type: application/json' -d '{
      "name": "'${INSTANCE_NAME}'",
      "description": "DESCRIPTION",
      "config": {
        "properties": {
          "livy.ingress.enabled": "true",
          "spark.version": "3.2.0"
        },
        "resources": {
          "cpu_requests": "20",
          "mem_requests": "80Gi"
        },
        "chartValueOverrides": {
          "dex-app": {
            "dexapp.api.image.override": '$DOCKER_NAMESPACE_ROOT'/dex-runtime-api-server:'${VERSION}'-'${JIRA_NUM}'",
            "dexapp.api.image.pullPolicy": "Always"
          }
        }
      }
    }' -s -b cdp-session-token=${CST} $dex_deploy_url | jq
}

function dex-vc-logs-runtime-api {
  if [[ -z $CLUSTER_ID ]]; then
        echo "CLUSTER_ID is not defined"
        return 1
  fi

  if [[ -z $DEX_APP_NS ]]; then
        echo "DEX_APP_NS is not defined"
        return 1
  fi

  set -x
  # TODO k8s grep replace with yaml expression
  DEX_API_POD=$(cst;dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get pods | grep -o -e "dex-app-.*-api-\S*")
  echo "API pod: $DEX_API_POD"
  cst;dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS logs -f $DEX_API_POD
  set +x
}


function dex-namespace-shell {
  if [[ $# -ne 1 ]]; then
    echo "Usage: dex-namespace-shell [namespace]"
    return 1
  fi

  CLUSTER_ID="${CLUSTER_ID:-noclusterid}"
  DEX_APP_NS=$1

  if [[ "$CLUSTER_ID" == 'noclusterid' ]]; then
        echo "CLUSTER_ID should be set"
        return 1
  fi

  cst && dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst zsh
}

function dex-stern-dex-api {
  if [[ $# -ne 1 ]]; then
    echo "Usage: dex-stern-dex-api [namespace]"
    return 1
  fi

  CLUSTER_ID="${CLUSTER_ID:-noclusterid}"
  DEX_APP_NS=$1

  if [[ "$CLUSTER_ID" == 'noclusterid' ]]; then
        echo "CLUSTER_ID should be set"
        return 1
  fi

  cst && dexw -a cst --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv stern -n $DEX_APP_NS -l app.kubernetes.io/name=dex-app-api
}

function dex-k9s-connect-service-privatestack {
  dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv --csi-workspace $USER k9s
}

function dex-k9s-connect-vc-privatestack {
  if [[ -z "$CLUSTER_ID" ]]; then
      echo "CLUSTER_ID should be set"
      return 1
  fi

  if [[ -z "$DEX_APP_NS" ]]; then
      echo "DEX_APP_NS should be set"
      return 1
  fi

  cst && dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst k9s --namespace $DEX_APP_NS
}

function dex-k9s-connect-cp-privatestack {
  mow-priv k9s
}

function dex-k9s-connect-mow-priv {
  mow-priv k9s -n $NAMESPACE_MOWPRIV
}


function dex-create-service-in-stack {
    cst; curl -H 'Content-Type: application/json' -d '{
      "name": "snemeth-cde-DEX-xxx",
      "env": "dex-priv-default-aws-env",
      "config": {
          "properties": {
              "loadbalancer.internal":"true",
              "cde.version": "1.19.0"
          },
          "resources": {
              "instance_type": "m5.2xlarge",
              "min_instances": "0",
              "max_instances": "10",
              "initial_instances": "0",
              "root_vol_size": "100"
          }
      }
  }' -s -b cdp-session-token=${CST}  https://snemeth-console.cdp-priv.mow-dev.cloudera.com/dex/api/v1/cluster

}

function dex-create-private-stack-mowpriv {
  if [[ $# -gt 0 ]]
  then
    mws=$1
  fi

  moonlander_workspace=""
  case $mws in
    (snemeth2) moonlander_workspace="$mws"  ;;
    (snemeth3) moonlander_workspace="$mws"  ;;
    (snemeth4) moonlander_workspace="$mws"  ;;
  esac
  _dex-create-private-stack "mow-priv"
}

function dex-create-private-stack-mowdev {
  moonlander_workspace=""
  _dex-create-private-stack "mow-dev"
}

function _dex-create-private-stack {
  #set -x
  local mow_env="$1"
  echo "Moonlander..."
  echo "git pull / running make..."
  cd $CSI_HOME/moonlander && git pull && make;


  if [[ -z $moonlander_workspace ]]
  then
    moonlander_workspace="$PRIVATE_STACK_CSI_WORKSPACE"
    echo "Failed to resolve Moonlander workspace to predefined workspace names! Defaulting to: $moonlander_workspace"
  fi

  gimme-aws-creds
  goto-dex
  # 1. make protos api-docs gen-mocks

  # 2. moonlander install
  DATE_OF_START=`date +%F-%H%M%S`
  logfilename="$HOME/.dex/logs/dexprivatestack_env-$mow_env""_""$DATE_OF_START.log"
  mkdir -p $HOME/.dex/logs/; touch $logfilename
  echo "****Logs are stored to file: $logfilename"


  # NOTE: Play around with these for debugging
  # export EXTRA_DOCKER_ARGS="--progress=plain --verbose"; echo "Exported EXTRA_DOCKER_ARGS=$EXTRA_DOCKER_ARGS"
  # export EXTRA_DOCKER_ARGS="--progress=plain"; echo "Exported EXTRA_DOCKER_ARGS=$EXTRA_DOCKER_ARGS"
  # export DOCKER_BUILD_WITH_NO_CACHE="true"; echo "Exported DOCKER_BUILD_WITH_NO_CACHE=$DOCKER_BUILD_WITH_NO_CACHE"
  # export ENABLE_MULTI_ARCH_BUILD="false"; echo "Exported ENABLE_MULTI_ARCH_BUILD=$ENABLE_MULTI_ARCH_BUILD"
  # TODO Specify skip build option?
  # https://stackoverflow.com/questions/40771781/how-to-append-a-string-in-bash-only-when-the-variable-is-defined-and-not-null
  MOONLANDER_SKIP_BUILD=1

  # stdout/stderr redirection: https://stackoverflow.com/questions/692000/how-do-i-write-standard-error-to-a-file-while-using-tee-with-a-pipe

  # TODO: piping to tee is not line buffered!
  #  Consider replacing it with 'script': https://unix.stackexchange.com/a/61833/189441
  if [[ "$mow_env" == "mow-dev" ]]; then
      mow-dev ./dev-tools/moonlander-cp.sh install $moonlander_workspace --ttl 168 2>&1 | tee "$logfilename"
      # mow-dev ./dev-tools/moonlander-cp.sh install ${USER} --ttl 168 --skip-build | tee "$logfilename"
  elif [[ "$mow_env" == "mow-priv" ]]; then
      # mow-priv ./dev-tools/moonlander-cp.sh install ${USER} --ttl 168 --skip-build | tee "$logfilename"
      mow-priv ./dev-tools/moonlander-cp.sh install $moonlander_workspace --ttl 168 2>&1 | tee "$logfilename"
  fi
  #set +x

  # mow-priv k9s --> Validate if snemeth pods are running (by name)
  # 3. Create service with curl: https://github.infra.cloudera.com/CDH/dex/wiki/Upgrade-Testing
  #### UNCOMMENT THIS TO CREATE SERVICE
  # dex-create-service-in-stack
}

function dex-start-upgrade-privatestack {
  cst;
  
  if [[ -z $CLUSTER_ID ]]; then
      echo "CLUSTER_ID must be set" >&2
      return 1
  fi


  dex_url="https://snemeth-console.cdp-priv.mow-dev.cloudera.com/dex"
  full_url="${dex_url}/api/v1/cluster/$CLUSTER_ID"
  echo "Starting to upgrade cluster with id: $CLUSTER_ID. Using DEX URL: $dex_url. Full URL: $full_url"
  
  set -x
  curl -X PATCH -H 'Content-Type: application/json' -d '{
      "upgrade": {
          "to_version": "latest"
      }
  }' -s -b cdp-session-token=${CST} ${full_url}
  set +x
}

function dex-save-logs-runtime-api-mow-priv-privatestack {
  DEX_CSI_WORKSPACE=$PRIVATE_STACK_CSI_WORKSPACE
  _dex-save-logs-runtime-api
}


function dex-save-logs-runtime-api-mow-priv {
  DEX_CSI_WORKSPACE=$DUMMY_CSI_WORKSPACE
  _dex-save-logs-runtime-api
}

function _dex-save-logs-runtime-api {
  set -x
  if [[ -z $CLUSTER_ID ]]; then
    echo "CLUSTER_ID is not defined"
    return 1
  fi

  if [[ -z $DEX_APP_NS ]]; then
    echo "DEX_APP_NS is not defined"
    return 1
  fi

  get-mow-priv-pods


  cst;
  mkdir -p /tmp/dexlogs-mowpriv/
  gen_files=()
  dexw_common_args=( -cst $CST --cluster-id $CLUSTER_ID --mow-env priv -w $DEX_CSI_WORKSPACE )
  dexw_k8s_common_args=( -n $DEX_APP_NS )


  echo "Saving logs from mow-priv pods. Cluster: $CLUSTER_ID, DEX APP: $DEX_APP_NS"
  for pod in ${mowpriv_pods}; do
      echo "Saving log from pod: $pod"
      dexw ${dexw_common_args[@]} kubectl ${dexw_k8s_common_args[@]} logs $pod > /tmp/dexlogs-mowpriv/$pod.log
      gen_files+=(/tmp/dexlogs-mowpriv/$pod.log)
  done
  echo "Generated files: ${gen_files[@]}"
  subl "${gen_files[@]}"
}

function get-pods-privatestack {
  _get-pods $NAMESPACE_PRIVATE_STACK "private stack"
}

function get-pods-mowpriv {
  _get-pods $NAMESPACE_MOWPRIV "mow-priv"
}

function _get-pods {
  local namespace=$1
  local mode=$2

  set -x
  echo "Getting $mode pods in namespace $namespace..."
  found_pods=()
  IFS=$'\n' read -r -d '' -A found_pods < <( kubectl -n $namespace get pods -l app.kubernetes.io/name=dex-cp -o json | jq -r '.items[].metadata.name' | sort | uniq && printf '\0' )
  # for pod in ${found_pods}; do
  #   echo "Found pod on $mode: $pod"
  # done
  echo "Found pods on $mode: ${found_pods[*]}"
  set +x
}

function get-mow-priv-pods {
  set -x
  if [[ -z $CLUSTER_ID ]]; then
    echo "CLUSTER_ID is not defined"
    return 1
  fi

  if [[ -z $DEX_APP_NS ]]; then
    echo "DEX_APP_NS is not defined"
    return 1
  fi

  cst;
  #DEX_CSI_WORKSPACE=$DUMMY_CSI_WORKSPACE
  dexw_common_args=( -cst $CST --cluster-id $CLUSTER_ID --mow-env priv -w $DEX_CSI_WORKSPACE )
  dexw_k8s_common_args=( -n $DEX_APP_NS )
  
  echo "Getting mow-priv pods..."
  mowpriv_pods=()
  IFS=$'\n' read -r -d '' -A mowpriv_pods < <( dexw ${dexw_common_args[@]} kubectl ${dexw_k8s_common_args[@]} get pods -l app.kubernetes.io/name=dex-app-api -o json | jq -r '.items[].metadata.name' | sort | uniq && printf '\0' )
  for pod in ${mowpriv_pods}; do
    echo "Found pod on mow-priv: $pod"
  done
  set +x
}


function dex-private-stack-deploy-dexcp-and-kickoff-upgrade {
    # Set up vars
    #dex_url="https://snemeth-console.cdp-priv.mow-dev.cloudera.com/dex"
    cst; echo $CST

    if [[ -z $CLUSTER_ID ]]; then
      echo "CLUSTER_ID must be set" >&2
      return 1
    fi
    echo "Using CLUSTER_ID: $CLUSTER_ID"


    # 1. Build CP, deploy CP to private stack / alias from linux-env
    dex-replace-dexcp-deployment-privatestack

    # 2. Initiate upgrade / 
    dex-start-upgrade-privatestack


    # 3.Save dexcp logs / alias from linux-env
    dex-save-logs-cp-privatestack2
}

function dex-replace-dexcp-deployment-privatestack {
  dex-export-common
  service_to_build="dex-cp"

  # 1. Build DEX-CP
  dex-build-cp
  
  set -x
  # 2. Get counter
  counter=$(_get_latest_counter_for_image | tail -1)
  tag="${VERSION}-${JIRA_NUM}-iteration-$counter"
  new_image=$DOCKER_NAMESPACE_ROOT/$service_to_build:$tag
  echo "new image: $new_image"

  set +x
  # 3. Replace deployment
  set -x
  kubectl -n $NAMESPACE_PRIVATE_STACK describe deployment snemeth-dex-dex-cp | grep -i image
  kubectl -n $NAMESPACE_PRIVATE_STACK set image deployment/snemeth-dex-dex-cp dex-cp=$new_image
  set +x

  #4. Get pods
  echo "sleeping 30 seconds..."
  sleep 30
  get-pods-privatestack

  echo "Showing pods (if image replaced the pods age should be new)"
  kubectl -n $NAMESPACE_PRIVATE_STACK get pods
  # for pod in ${found_pods}; do
  #   echo "pod: $pod"
    
  # done
}


function dex-replace-dexcp-privatestack {
  # TODO dupe of dex-replace-dexcp-deployment-privatestack ? 
  #- k9s -n snemeth-dex
  #- kubectl -n snemeth-dex describe deployment snemeth-dex-dex-cp | grep -i image
  #- kubectl -n snemeth-dex set image deployment/snemeth-dex-dex-cp dex-cp=docker-registry.infra.cloudera.com/snemeth/dex-cp:1.18.0-dev-DEX-7712-iteration-4
  if [[ -z $DEX_MOONLANDER_CP_IMAGE_TAG ]]; then
    echo "DEX_MOONLANDER_CP_IMAGE_TAG must be set"
    return 1
  fi

  # TODO Get latest iteration image tag
  # DEX_MOONLANDER_CP_IMAGE_TAG=1.18.0-dev-DEX-7712-iteration-4
  echo "DEX_MOONLANDER_CP_IMAGE_TAG=$DEX_MOONLANDER_CP_IMAGE_TAG"

  cst;
  goto-dex
  #export SKIP_BUILD=true
  #export DEX_IMAGE_TAG=$DEX_MOONLANDER_CP_IMAGE_TAG
  mow-priv ./dev-tools/moonlander-cp.sh install ${USER} --skip-build --version $DEX_MOONLANDER_CP_IMAGE_TAG
}


function dex-replace-runtime-mowpriv-privatestack {
  DEX_CSI_WORKSPACE=$PRIVATE_STACK_CSI_WORKSPACE
  _dex-replace-runtime-api-server
}

function dex-replace-runtime-mowpriv {
  DEX_CSI_WORKSPACE=$DUMMY_CSI_WORKSPACE 
  _dex-replace-runtime-api-server
}


function _dex-replace-runtime-api-server {
  set -x
  if [[ -z $CLUSTER_ID ]]; then
    echo "CLUSTER_ID is not defined"
    return 1
  fi

  dex-build-runtime
  if [ "$?" -ne 0 ]; then
    echo "Runtime build unsuccessful!"
    return 1
  fi


  # Get latest image tag for runtime api server
  service_to_build="dex-runtime-api-server"
  counter=$(_get_latest_counter_for_image | tail -1)
  tag="${VERSION}-${JIRA_NUM}-iteration-$counter"
  new_image=$DOCKER_NAMESPACE_ROOT/$service_to_build:$tag
  echo "Parsed docker image: $new_image"

  cst;

  # setup common args
  dexw_common_args=( -cst $CST --cluster-id $CLUSTER_ID --mow-env priv -w $DEX_CSI_WORKSPACE )
  dexw_k8s_common_args=( -n $DEX_APP_NS )
  

  if [[ -z $DEX_APP_NS ]]; then
    # Get and store dex-app's Namespace from Private stack
    # TODO k8s grep replace with yaml expression
    DEX_APP_NS=$(dexw ${dexw_common_args[@]} kubectl -n $NAMESPACE_MOWPRIV get namespaces | grep "dex-app-" | awk '{print $1}' 2>/dev/null | tail -n 1)
    export DEX_APP_NS
    echo "Fetched namespace of dex-app: $DEX_APP_NS"
  else
    echo "Found cached namespace of dex-app: $DEX_APP_NS"
  fi

  if [[ -z $DEX_APP_DEPL ]]; then
    # Get dex-app-api deployment from dex-app namespace
    # TODO k8s grep replace with yaml expression
    DEX_APP_DEPL=$(dexw ${dexw_common_args[@]} kubectl -n $DEX_APP_NS get deployments  | grep "dex-app.*-api" | awk '{print $1}' 2>/dev/null | tail -n 1)
    export DEX_APP_DEPL
    echo "Fetched deployment of dex-app-api: $DEX_APP_DEPL"
  else
      echo "Found cached deployment of dex-app: $DEX_APP_DEPL"
  fi

  # Uncomment to describe deployment
  # dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS describe deployment $DEX_APP_DEPL

  echo "Listing original image of $service_to_build: "
  # TODO k8s grep replace with yaml expression
  dexw ${dexw_common_args[@]} kubectl ${dexw_k8s_common_args[@]} describe deployment $DEX_APP_DEPL | grep -i image

  dexw ${dexw_common_args[@]} kubectl ${dexw_k8s_common_args[@]} set image deployment/$DEX_APP_DEPL dex-app-api=$new_image

  echo "Listing modified image of $service_to_build: "
  # TODO k8s grep replace with yaml expression
  dexw ${dexw_common_args[@]} kubectl ${dexw_k8s_common_args[@]} describe deployment $DEX_APP_DEPL | grep -i image

  dexw ${dexw_common_args[@]} kubectl ${dexw_k8s_common_args[@]} get pods
  set +x
}

function dex-follow-logs-runtimeapi-privatestack {
  if [[ -z $CLUSTER_ID ]]; then
        echo "CLUSTER_ID is not defined"
        return 1
  fi

  if [[ -z $DEX_APP_NS ]]; then
        echo "DEX_APP_NS is not defined"
        return 1
  fi

  # TODO k8s grep replace with yaml expression
  DEX_API_POD=$(dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get pods | grep -o -e "dex-app-.*-api-\S*")
  echo "API pod: $DEX_API_POD"
  dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS logs -f $DEX_API_POD
}

function dex-follow-logs-runtimeapi-grep-privatestack {
  local grepfor="$1"
  # TODO k8s grep replace with yaml expression
  DEX_API_POD=$(dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get pods | grep -o -e "dex-app-.*-api-\S*")
  echo "API pod: $DEX_API_POD"
  dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS logs -f $DEX_API_POD | grep $grepfor
}

function dex-follow-logs-dexcp-1-privatestack {
  local namespace="$NAMESPACE_PRIVATE_STACK"
  get-pods-privatestack

  _dex-follow-log "private-stack" $namespace ${found_pods[1]}
}

function dex-follow-logs-dexcp-2-privatestack {
  local namespace="$NAMESPACE_PRIVATE_STACK"
  get-pods-privatestack
  _dex-follow-log "private-stack" $namespace ${found_pods[2]}
}


function dex-save-logs-cp-privatestack {
  local namespace="$NAMESPACE_PRIVATE_STACK"
  local target_dir="/tmp/dexlogs-privatestack/"

  get-pods-privatestack
  _dex-save-logs "private-stack" $namespace $target_dir
}

function dex-save-logs-cp-privatestack-custom {
  set -x
  NAMESPACE_PRIVATE_STACK_OLD=$NAMESPACE_PRIVATE_STACK
  NAMESPACE_PRIVATE_STACK="$1"
  local namespace="$NAMESPACE_PRIVATE_STACK"
  local target_dir="/tmp/dexlogs-privatestack-ns-$namespace/"

  get-pods-privatestack
  _dex-save-logs "private-stack" $namespace $target_dir

  # restore
  NAMESPACE_PRIVATE_STACK=$NAMESPACE_PRIVATE_STACK_OLD
}

function dex-kubectl-commands-save-logs-cp-privatestack {
  get-pods-privatestack
}


function dex-save-logs-cp-mowpriv {
  local namespace="$NAMESPACE_MOWPRIV"
  local target_dir="/tmp/dexlogs-mowpriv/"

  get-pods-mowpriv
  _dex-save-logs "mow-priv" $namespace $target_dir
}

function dex-save-logs-cp-mowpriv-custom-ns {
  local namespace="$1"
  local target_dir="/tmp/dexlogs-mowpriv-$namespace/"

  _get-pods $namespace "mow-priv"
  _dex-save-logs "mow-priv" $namespace $target_dir
}



function _dex-save-logs {
  set -x
  local mode=$1
  local namespace=$2
  local target_dir=$3

  mkdir -p $target_dir
  echo "Saving logs from $mode pods..."

  #while IFS= read -r pod; do
  for pod in ${found_pods}; do
    echo "Actual pod: $pod"
    local target_file="$target_dir/pod-log-$pod.txt"
    echo "Saving logs from pod: $pod to $target_file"
    kubectl -n $namespace logs $pod > $target_file

    if [[ $DEX_CFG_GREP_IN_LOGS == 1 ]]; then
      local target_file_grep="$target_dir/pod-log-$pod-grep.txt"
      grep $DEX_CFG_GREP_IN_LOGS $target_file > $target_file_grep
    fi

    
  done
  #done <<< ${found_pods[*]}


  echo "To copy the files, execute these: "
  for pod in ${found_pods}; do
  #while IFS= read -r pod; do
    echo "find $target_dir/ -type f -iregex \".*pod-log-$pod.*\" -exec cp {} \$RES_DIR \;"
  done
  #done <<< $found_pods


  echo "Listing result files..."
  #while IFS= read -r pod; do
  for pod in ${found_pods}; do
    ls -latr $target_dir/pod-log-$pod-*
  #done <<< $found_pods
  done
    
  set +x
}


function _dex-follow-log {
  set -x
  local mode=$1
  local namespace=$2
  local pod=$3

  echo "Following log from $mode pod..."

  echo "Current pod: $pod"
  kubectl -n $namespace logs -f $pod
  set +x
}

function dex-launch-jobs {
  # Jira with commands: https://jira.cloudera.com/browse/DEX-7217
  goto-dex

  # UNCOMMENT THIS TO CREATE SLEEPER RESOURCE
  # build/cde resource create --name sleeper
  # build/cde resource upload --name sleeper --local-path sleep.py

  JOB_LIMIT=10

  # Create jobs
  for ((i=0;i<$JOB_LIMIT;i++)); do yes yes | build/cde job create --name sleep_py_$i --type spark --application-file sleep.py --mount-1-resource sleeper; done

  # Run jobs
  for ((i=0;i<$JOB_LIMIT;i++)); do yes yes | build/cde --auth-pass-file  ~/.cdp/workload_pass  job run --name sleep_py_$i; done
}


function dex-dexk {
    CLUSTER_ID=$1
    if [[ -z $CLUSTER_ID ]]; then
        echo "Usage: dex-dexk cluster-id" >&2
        return 1
    fi
    cst && dexk --cluster-id $clusterId --cdp-token $CST --ingress dex --mow-env priv --workspace-name ${USER}
}

function dex-pvc-get-vault-kubeconfig {
  export VAULT_ADDR="https://vault-shared-os-dev-01-control-plane-vault.apps.shared-os-dev-01.kcloud.cloudera.com/"
  export VAULT_SKIP_VERIFY="True"
  vault login -method=ldap username=snemeth@cloudera.com
  # TODO Complete this function and figure out what's the issue with vault login
}

function dex-print-dexw-guidance {
  echo "Connect to mow-priv cluster:"
  echo "dexw -v --cluster-id \$CLUSTER_ID -cst \$CST --mow-env priv --auth cst k9s -n \$DEX_APP_NS"

  echo "Connect to mow-priv service:"
  echo "dexw -v --cluster-id \$CLUSTER_ID -cst \$CST --mow-env priv --auth cst k9s"
}

function download-pod-logs-all-containers {
  # CLUSTER_ID=cluster-7kwp5npg
  # DEX_APP_NS=dex-app-hvwlfmgs 

  #cst && dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst k9s
  #dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst kubectl get pods -l app.kubernetes.io/name=dex-cp
  # dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst kubectl get pods -l app.kubernetes.io/instance=dex-base -l app.kubernetes.io/name=nginx       
  #dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst kubectl logs $KNOXPOD -n $DEX_APP_NS
  DEX_NGINX_CONTR_POD=$(dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst kubectl -n dex get pods -l app.kubernetes.io/instance=dex-base -l app.kubernetes.io/name=nginx --no-headers | awk '{print $1}')
  echo "nginx controller pod: $DEX_NGINX_CONTR_POD"

  CONTAINERS=($(dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst kubectl -n dex get pods $DEX_NGINX_CONTR_POD -o jsonpath='{.spec.containers[*].name}'))
  for cont in ${CONTAINERS}; do
    echo "Getting logs of: $DEX_NGINX_CONTR_POD/$cont" 
    target_file="/tmp/pod-$DEX_NGINX_CONTR_POD-cont-$cont.log"
    echo "Writing log to $target_file"
    dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst kubectl -n dex logs $DEX_NGINX_CONTR_POD -c $cont > $target_file
  done
}

function dex-get-liftie-data {
  # PREREQUISITE
  # Run this in other terminal
  # TODO: auto-check if port forward is enabled?
  # mow-priv kubectl port-forward -n computex service/computex-app-cpx-liftie 9999:9999

  # Example: 
  # dex-get-liftie-data "cluster-kdwgl8pp" "liftie-0581y84l" "snemeth-console"

  if [ "$#" -ne 3 ]; then
      echo "Usage: dex-get-liftie-data <CLUSTER_ID> <PROVISIONER_ID> <PRIVATE_STACK_NAME>"
      return 1
  fi

  CLUSTER_ID="$1"
  PROVISIONER_ID="$2"
  PRIVATE_STACK_NAME="$3"
  
  cst;
  set -x
  curl -H 'Content-Type: application/json' -s -b cdp-session-token=$CST "https://$PRIVATE_STACK_NAME.cdp-priv.mow-dev.cloudera.com/dex/api/v1/cluster/$CLUSTER_ID?pollProvisioner=true" | jq -r ".clusterInfo.ProvisionerClusterView" | base64 -d | yq r - > ./cluster-view-$PROVISIONER_ID
  set +x
  
  # Setup
  INGRESS_PATH=dex
  export ACTOR_CRN=`curl -s -b cdp-session-token=${CST} "https://$PRIVATE_STACK_NAME.cdp-priv.mow-dev.cloudera.com/${INGRESS_PATH}/api/v1/cluster/${CLUSTER_ID}" | jq -r '.clusterInfo.CreatorCRN'`
  export LIFTIE_ID=`curl -s -b cdp-session-token=${CST} "https://$PRIVATE_STACK_NAME.cdp-priv.mow-dev.cloudera.com/${INGRESS_PATH}/api/v1/cluster/${CLUSTER_ID}" | jq -r '.provisionerid'`
  export TENANT_ID=`curl -s -b cdp-session-token=${CST} "https://$PRIVATE_STACK_NAME.cdp-priv.mow-dev.cloudera.com/${INGRESS_PATH}/api/v1/cluster/${CLUSTER_ID}" | jq -r '.tenantId'`
  echo "ACTOR_CRN=${ACTOR_CRN}"
  echo "LIFTIE_ID=${LIFTIE_ID}"
  echo "TENANT_ID=${TENANT_ID}"


  curl -s \
  -H "X-Cdp-Actor-Crn: ${ACTOR_CRN}" \
  -H "X-Cdp-Request-Id: `uuidgen`" \
  "http://localhost:9999/liftie/api/v1/cluster/${LIFTIE_ID}" > ./cluster-record-$PROVISIONER_ID
}



function dex-change-deployment-image-privatestack {
  # k9s deployments
  # NS: cadence-97gmh4cz, DEPL: cadence-api-server
  # NS: cadence-worker-rm-97gmh4cz, DEPL: dex-cadence-worker

  # k8s SELECTORS
  # https://stackoverflow.com/questions/52957227/kubectl-command-to-list-pods-of-a-deployment-in-kubernetes
  # dex-cadence-worker: Selector:               app.kubernetes.io/instance=dex-cadence-worker,app.kubernetes.io/name=dex-cadence-worker 
  # cadence-api-server: Selector:               app.kubernetes.io/component=api-server,app.kubernetes.io/instance=dex-cadence,app.kubernetes.io/name=dex-cadence


  if [ "$#" -ne 3 ]; then
      # echo "Usage: dex-change-deployment-image-privatestack <CLUSTER_ID> <DEPLOYMENT_NAME> <NAME_SELECTOR> <NEW_IMAGE_NAME>"
      echo "Usage: dex-change-deployment-image-privatestack <CLUSTER_ID> <DEPLOYMENT_TYPE> <NEW_IMAGE_NAME>"
      return 1
  fi


  local curr_date=`date +%F-%H%M%S`
  local cluster_id="$1"
  local depl_type="$2"
  local new_image_name="$3"
  # Note: Container name in deployment descriptor will be the same as name of the deployment
  # L_CONTAINER_NAME="$depl_name"


  set -x
  # Set up vars
  DEX_CSI_WORKSPACE=$PRIVATE_STACK_CSI_WORKSPACE
  cst;
  dexw_args=( -cst $CST --cluster-id $cluster_id --mow-env priv -w $DEX_CSI_WORKSPACE )
  dexw_k8s_args=( -n $DEX_APP_NS )
  
  

  # Set DEX app namespace
  if [[ -z $DEX_APP_NS ]]; then
    # Get and store dex-app's Namespace from Private stack
    # TODO k8s grep replace with yaml expression
    DEX_APP_NS=$(dexw ${dexw_args[@]} kubectl -n $NAMESPACE_MOWPRIV get namespaces | grep "dex-app-" | awk '{print $1}' 2>/dev/null | tail -n 1)
    export DEX_APP_NS
    echo "Fetched namespace of dex-app: $DEX_APP_NS"
  else
    echo "Found cached namespace of dex-app: $DEX_APP_NS"
  fi


  # Get Cadence namespace names
  cadence_namespaces=$(dexw ${dexw_args[@]} kubectl -n $NAMESPACE_MOWPRIV get namespaces | grep "cadence-" | awk '{print $1}' 2>/dev/null)
  echo "Cadence namespaces: $cadence_namespaces"

  cadence_worker_ns=$(echo $cadence_namespaces | grep cadence-worker-rm-.\*)
  cadence_api_server_ns=$(echo $cadence_namespaces | grep -v cadence-worker-rm-.\*)

  echo "cadence_worker_ns: $cadence_worker_ns"
  echo "cadence_api_server_ns: $cadence_api_server_ns"


  if [[ "$depl_type" == 'cadence-worker' ]]; then
        local cadence_namespace="$cadence_worker_ns"
        local depl_name="dex-cadence-worker"
  
  elif [[ "$depl_type" == 'cadence-api-server' ]]; then
        local cadence_namespace="$cadence_worker_ns"
        local depl_name="cadence-api-server"
  else
        echo "Wrong cadence deployment type!"
        return 1
  fi


  dexw_k8s_args=( -n $cadence_namespace )
  # 1. Get + Save original deployment
  echo "Listing deployment: $depl_name"
  target_file="/tmp/describe-deployment-$cluster_id-$depl_name-orig-$curr_date.txt"
  dexw ${dexw_args[@]} kubectl ${dexw_k8s_args[@]} describe deployment $depl_name > "$target_file"

  if [ "$?" -ne 0 ]; then
    echo "Failed to list deployment: $depl_name"
    return 1
  fi

  echo "Saved original deployment to: $target_file"
  echo "Printing original image of deployment: $depl_name"
  grep -i image "$target_file"


  # 2. Modify deployment
  target_file="/tmp/describe-deployment-$cluster_id-$depl_name-new-$curr_date.txt"

  echo "Scaling down deployment: $depl_name" # Required because: https://stackoverflow.com/a/64248490/1106893
  dexw ${dexw_args[@]} kubectl ${dexw_k8s_args[@]} scale --replicas=1 deployment/$depl_name
  

  echo "Setting new image: $new_image_name for deployment: $depl_name"
  dexw ${dexw_args[@]} kubectl ${dexw_k8s_args[@]} set image deployment/$depl_name $depl_name=$new_image_name
  dexw ${dexw_args[@]} kubectl ${dexw_k8s_args[@]} describe deployment $depl_name > "$target_file"
  echo "Saved modified deployment to: $target_file"
  echo "Listing modified image of deployment: $depl_name"
  grep -i image "$target_file"


  # 3. List pods of modified deployment
  echo "Listing pods of new deployment: $depl_name"
  dexw ${dexw_args[@]} kubectl ${dexw_k8s_args[@]} get pods -l app.kubernetes.io/name=$name_selector
  set +x
}

function dex-analyse-gbn-tests {
  # PREREQUISITE #1: https://github.com/jstemmer/go-junit-report
  # INSTALLATION: go install github.com/jstemmer/go-junit-report/v2@latest

  # PREREQUISITE #2: https://github.com/inorton/junit2html
  # INSTALLATION: pip3 install junit2html


  # Example invocation
  # dex-analyse-gbn-tests /Users/snemeth/Downloads/cde-flaky-tests-and-failed-builds

  # START LINE
  # 2024-05-08 22:04:14 - INFO-root::util|431:: go test -count=1 -timeout 15m -race  ./cmd/... ./lib/... ./pkg/...[0m

  # END LINE
  # 2024-05-08 22:16:18 - INFO-root::util|431:: make: *** [Makefile:118: gotest] Error 1[0m

  local main_dir="$1"

  # 1. Find build.log file from main GBN dir
  local files=$(find $main_dir -iname build.log)

  IFS=$'\n'
  files=($(find $main_dir -iname build.log))
  unset IFS

  echo "Generating JUnit report HTML files..."
  # set -x
  for file in "${files[@]}"
  do
    dest_dir=$(dirname $file)
    
    # 2. Find start line
    start_line=$(loganalysis-get-linenumber-for-pattern $file "go test ")

    # 3. Find end line
    end_line=$(loganalysis-get-linenumber-for-pattern $file "Makefile.*gotest")

    if [[ ! "$start_line" || ! "$end_line" ]]; then
        echo "Skipping file: $file" 
        # echo "Skipping file: $file as start line and end line for Go test was not found!"
        continue
    fi

    local split="/tmp/split_$(date +%s).txt"
    loganalysis-split-file $start_line $end_line $file $split

    cat $split | go-junit-report -set-exit-code > $dest_dir/junit_report.xml
    python -m junit2htmlreport $dest_dir/junit_report.xml $dest_dir/junit_report.html

    echo "Generated file: $dest_dir/junit_report.html"

    # Uncomment if you don't want to open files
    open $dest_dir/junit_report.html
  done
  # set +x
}


###################################################################### DEX RUNTIME ######################################################################

dex-export-gopath



######### 

