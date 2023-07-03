#!/usr/bin/env bash

echo "Setting up DEX env..."

############## VARS ##############
DOCKER_ROOT_CLOUDERA="docker-registry.infra.cloudera.com"
DEX_DOCKER_IMAGES_GENERATED_FILE="$DEX_DEV_ROOT/cloudera/docker_images.generated.yaml"


############## VARS ##############

# asdf setup
. /usr/local/opt/asdf/libexec/asdf.sh

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
	export GOPATH=$(go env GOPATH)
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
  DEX_API_POD=$(cst;dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get pods | grep -o -e "dex-app-.*-api-\S*")
  echo "API pod: $DEX_API_POD"
  cst;dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS logs -f $DEX_API_POD
  set +x
}

function dex-namespace-k9s {
  if [[ -z "$CLUSTER_ID" ]]; then
        echo "CLUSTER_ID should be set"
        return 1
  fi

  if [[ -z "$DEX_APP_NS" ]]; then
        echo "DEX_APP_NS should be set"
        return 1
  fi

  set -x
  cst && dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env priv --auth cst k9s --namespace $DEX_APP_NS
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

function dex-private-stack-connect-to-service {
  dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv --csi-workspace $USER k9s
}

function dex-private-stack-connect-to-cp {
  mow-priv k9s
}


function dex-create-service-in-stack {
    cst; curl -H 'Content-Type: application/json' -d '{
      "name": "snemeth-cde-DEX-7712",
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
  _dex-create-private-stack "mow-priv"
}

function dex-create-private-stack-mowdev {
  _dex-create-private-stack "mow-dev"
}

function _dex-create-private-stack {
  set -x
  local mow_env="$1"
  echo "Moonlander..."
  echo "git pull / running make..."
  cd $CSI_HOME/moonlander && git pull && make;


  gimme-aws-creds
  goto-dex
  # 1. make protos api-docs gen-mocks

  # 2. moonlander install
  DATE_OF_START=`date +%F-%H%M%S`
  logfilename="$HOME/.dex/logs/dexprivatestack_env-$mow_env""_""$DATE_OF_START.log"
  touch $logfilename

  if [[ "$mow_env" == "mow-dev" ]]; then
      mow-dev ./dev-tools/moonlander-cp.sh install ${USER} --ttl 168 | tee "$logfilename"
      # mow-dev ./dev-tools/moonlander-cp.sh install ${USER} --ttl 168 --skip-build | tee "$logfilename"
  elif [[ "$mow_env" == "mow-priv" ]]; then
      mow-priv ./dev-tools/moonlander-cp.sh install ${USER} --ttl 168 | tee "$logfilename"
  fi
  set +x

  # mow-priv k9s --> Validate if snemeth pods are running (by name)
  # 3. Create service with curl: https://github.infra.cloudera.com/CDH/dex/wiki/Upgrade-Testing
  #### UNCOMMENT THIS TO CREATE SERVICE
  # dex-create-service-in-stack
}

function dex-private-stack-replace-dexcp {
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

function dex-private-stack-replace-dexcp-deployment {
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
  kubectl -n snemeth-dex describe deployment snemeth-dex-dex-cp | grep -i image
  kubectl -n snemeth-dex set image deployment/snemeth-dex-dex-cp dex-cp=$new_image
  set +x

  #4. Get pods
  echo "sleeping 30 seconds..."
  sleep 30
  get-private-stack-pods

  echo "Showing pods (if image replaced the pods age should be new)"
  kubectl -n snemeth-dex get pods
  # for pod in ${snemeth_pods}; do
  #   echo "pod: $pod"
    
  # done
}

function dex-private-stack-upgrade-start {
  cst;
  
  dex_url="https://snemeth-console.cdp-priv.mow-dev.cloudera.com/dex"
  full_url="${dex_url}/api/v1/cluster/$CLUSTER_URL"
  echo "Starting to upgrade cluster: $CLUSTER_URL. Using DEX URL: $dex_url. Full URL: $full_url"
  
  set -x
  curl -X PATCH -H 'Content-Type: application/json' -d '{
      "upgrade": {
          "to_version": "latest"
      }
  }' -s -b cdp-session-token=${CST} ${full_url}
  set +x
}

function dex-private-stack-save-dexcp-logs {
  get-private-stack-pods

    mkdir -p /tmp/dexlogs/
    gen_files=()

    echo "Saving logs from private stack pods..."
    for pod in ${snemeth_pods}; do
        echo "Saving log from pod: $pod"
        #kubectl -n snemeth-dex logs $pod | grep "\*\*" | tee /tmp/dexlogs/$pod-grep.log
        #gen_files+=(/tmp/dexlogs/$pod-grep.log)
        kubectl -n snemeth-dex logs $pod > /tmp/dexlogs/$pod.log
        gen_files+=(/tmp/dexlogs/$pod.log)
    done
    subl "${gen_files[@]}"
}

function get-private-stack-pods {
  echo "Getting private stack pods..."
  snemeth_pods=()
  IFS=$'\n' read -r -d '' -A snemeth_pods < <( kubectl -n snemeth-dex get pods -l app.kubernetes.io/name=dex-cp -o json | jq -r '.items[].metadata.name' | sort | uniq && printf '\0' )
  for pod in ${snemeth_pods}; do
    echo "Found pod: $pod"
  done
}


function dex-private-stack-deploy-dexcp-and-kickoff-upgrade {
    # Set up vars
    #dex_url="https://snemeth-console.cdp-priv.mow-dev.cloudera.com/dex"
    cst; echo $CST

    # TODO verify if CLUSTER_URL is set!
    echo "Using CLUSTER_URL: $CLUSTER_URL"


    # Build CP, deploy CP to private stack / alias from linux-env
    dex-private-stack-replace-dexcp-deployment 


    # Initiate upgrade / 
    dex-upgrade-start


    # Save dexcp logs / alias from linux-env
    dex-private-stack-save-dexcp-logs
}


function dex-private-stack-replace-runtime {
  if [[ -z $CLUSTER_ID ]]; then
        echo "CLUSTER_ID is not defined"
        return 1
  fi

  NEW_IMAGE_TAG="$1"

  # TODO Determine latest image for runtime (iteration-*)
  if [[ -z $NEW_IMAGE_TAG ]]; then
        echo "Usage: dex-private-stack-replace-runtime <new image tag>"
        return 1
  fi

  cst

  if [[ -z $DEX_APP_NS ]]; then
    # Get and store dex-app's Namespace from Private stack
	  DEX_APP_NS=$(dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n dex get namespaces | grep "dex-app-" | awk '{print $1}' 2>/dev/null | tail -n 1)
	  export DEX_APP_NS
	  echo "Queried namespace of dex-app: $DEX_APP_NS"
	else
	  echo "Found cached namespace of dex-app: $DEX_APP_NS"
	fi

  if [[ -z $DEX_APP_DEPL ]]; then
    # Get dex-app-api deployment from dex-app namespace
    DEX_APP_DEPL=$(dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get deployments  | grep "dex-app.*-api" | awk '{print $1}' 2>/dev/null | tail -n 1)
    export DEX_APP_DEPL
    echo "Queried deployment of dex-app-api: $DEX_APP_DEPL"
  else
      echo "Found cached deployment of dex-app: $DEX_APP_DEPL"
  fi

	# Uncomment to describe deployment
	# dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS describe deployment $DEX_APP_DEPL

  echo "Listing original image of dex-app-api (runtime): "
	dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS describe deployment $DEX_APP_DEPL | grep -i image

  dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS set image deployment/$DEX_APP_DEPL dex-app-api=$DOCKER_ROOT_CLOUDERA/snemeth/dex-runtime-api-server:$NEW_IMAGE_TAG

  echo "Listing modified image of dex-app-api (runtime): "
	dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS describe deployment $DEX_APP_DEPL | grep -i image

	dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get pods
}

function dex-private-stack-get-logs-follow {
  if [[ -z $CLUSTER_ID ]]; then
        echo "CLUSTER_ID is not defined"
        return 1
  fi

  if [[ -z $DEX_APP_NS ]]; then
        echo "DEX_APP_NS is not defined"
        return 1
  fi

  DEX_API_POD=$(dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get pods | grep -o -e "dex-app-.*-api-\S*")
  echo "API pod: $DEX_API_POD"
  dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS logs -f $DEX_API_POD
}

function dex-private-stack-get-logs-followgrep {
  local grepfor="$1"
  DEX_API_POD=$(dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get pods | grep -o -e "dex-app-.*-api-\S*")
  echo "API pod: $DEX_API_POD"
  dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS logs -f $DEX_API_POD | grep $grepfor
}

function dex-private-stack-save-logs-cp {
  #set -x
  local namespace="snemeth-dex"
  local grep_for="\*\*"
  
  cp_pods=$(kubectl -n $namespace get pods --no-headers -o custom-columns=":metadata.name")
  #for pod in $cp_pods 
  while IFS= read -r pod; do
    local target_file="/tmp/pod-log-$pod-full.txt"
    local target_file_grep="/tmp/pod-log-$pod-grep.txt"
    echo "Saving logs from pod: $pod to $target_file"
    kubectl -n $namespace logs $pod > $target_file
    grep $grep_for $target_file > $target_file_grep
    
  done <<< $cp_pods


  echo "To copy the files, execute these: "
  while IFS= read -r pod; do
    echo "find /tmp/ -type f -iregex \".*pod-log-$pod.*\" -exec cp {} \$RES_DIR \;"
  done <<< $cp_pods

  echo "Listing result files..."
  while IFS= read -r pod; do
    ls -latr /tmp/pod-log-$pod-*
  done <<< $cp_pods
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

###################################################################### DEX RUNTIME ######################################################################

dex-export-gopath