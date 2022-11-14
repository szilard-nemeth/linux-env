#!/usr/bin/env bash

echo "Setting up DEX env..."
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
export PATH=$PATH:$CSI_HOME/bin:$CSI_HOME/moonlander:$DEX_DEV_TOOLS


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
function cst () {
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

function dex-default-env() {
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

function dex-export-runtime-build-env() {
	export JIRA_NUM=$(git rev-parse --abbrev-ref HEAD)
	export VERSION=1.18.0-dev
	export INSTANCE_NAME=snemeth-test
	export REGISTRY_NAMESPACE=${USER}
	export CLUSTER_ID=$1
	# should be simply 'dex' if using main mow-dev CDE service
	export INGRESS_PATH=dex

	echo "##############################################"
	echo "# JIRA_NUM=$JIRA_NUM"
	echo "# VERSION=$VERSION"
	echo "# INSTANCE_NAME=$INSTANCE_NAME"
	echo "# REGISTRY_NAMESPACE=$REGISTRY_NAMESPACE"
	echo "# CLUSTER_ID=$CLUSTER_ID"
	echo "# INGRESS_PATH=$INGRESS_PATH"
	echo "##############################################"
}


function _dex-build {
  if [ $# -ne 1 ]; then
    echo "Usage: _dex-build <service>" 1>&2
    exit 1
  fi
  service_to_build="$1"

  if [ -z ${REGISTRY_NAMESPACE+x} ]; then
			echo "REGISTRY_NAMESPACE is not set. Call 'dex-export-runtime-build-env' first";
			return
		else
			echo "REGISTRY_NAMESPACE set to '$REGISTRY_NAMESPACE'";
		fi


    # Should call manually: dex-export-runtime-build-env
  	cd $DEX_DEV_ROOT/docker
    make $service_to_build

    echo "Listing images..."
    docker images | grep $service_to_build | grep $VERSION
    docker tag docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:${VERSION} docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:${VERSION}-${JIRA_NUM}
    # docker tag docker-registry.infra.cloudera.com/cloudera/dex/$service_to_build:${VERSION} docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:${VERSION}-${JIRA_NUM}
    docker push docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:${VERSION}-${JIRA_NUM}
    cd -
}

function _dex-increase-docker-tag-counter {
  if [ $# -ne 1 ]; then
    echo "Usage: _dex-increase-docker-tag-counter <service>" 1>&2
    exit 1
  fi
  service_to_build="$1"

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

  #docker-registry.infra.cloudera.com/snemeth/dex-runtime-api-server 1.18.0-dev-DEX-7712 06bb27949544 2 hours ago 646MB
  arr=($(docker images | grep $service_to_build | grep $JIRA_NUM-iteration- | grep $VERSION-$JIRA_NUM | tail -n 1 | tr -s ' '))

  if [[ ${#arr[@]} == 0 ]];then
    echo "Counter not found for Docker image '${arr[1]}'"
    counter=0
  else
    unset counter
    d_tag=${arr[2]}
    [[ $d_tag =~ '^[0-9A-Za-z_\.\-]+-iteration-([0-9]+)$' ]] && counter=$match[1]

    if [[ -z $counter ]]; then
      echo "Counter not found for Docker image '${arr[1]}'"
      counter=0
    fi
  fi

  echo "Current tag counter for Docker image '${arr[1]}': $counter"
  let "counter++"
  echo "Increased tag counter for Docker image '${arr[1]}': $counter"

  new_tag="${VERSION}-${JIRA_NUM}-iteration-$counter"

  docker tag docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:${VERSION} docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:$new_tag
  docker push docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:$new_tag

  # TODO Filter images with docker images itself - https://stackoverflow.com/questions/24659300/how-to-use-docker-images-filter
  docker images | grep docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:$new_tag

  echo "Use this image to replace service:"
  echo "docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/$service_to_build:$new_tag"
}

function dex-build-runtime {
  _dex-build "dex-runtime-api-server"
  _dex-increase-docker-tag-counter "dex-runtime-api-server"
}

function dex-build-cp {
  _dex-build "dex-cp"
  _dex-increase-docker-tag-counter "dex-cp"
}

function dex-deploy-runtime-dev-auto {
  # Setting the pull policy to always means you can push multiple iterations to the same docker tag when testing.

  dex_deploy_url="https://console.dps.mow-dev.cloudera.com/${INGRESS_PATH}/api/v1/cluster/${CLUSTER_ID}/instance"
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
	          "dexapp.api.image.override": "docker-registry.infra.cloudera.com/'${REGISTRY_NAMESPACE}'/dex-runtime-api-server:'${VERSION}'-'${JIRA_NUM}'",
	          "dexapp.api.image.pullPolicy": "Always"
	        }
	      }
	    }
	  }' -s -b cdp-session-token=${CST} $dex_deploy_url | jq
}

function dex-namespace-k9s {
  if [[ $# -ne 1 ]]; then
    echo "Usage: dex-k9s-namespace [namespace]"
    return 1
  fi

  CLUSTER_ID="${CLUSTER_ID:-noclusterid}"
  DEX_NS=$1

  if [[ "$CLUSTER_ID" == 'noclusterid' ]]; then
        echo "CLUSTER_ID should be set"
        return 1
  fi

  cst && dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env dev --auth cst k9s --namespace $DEX_NS
}

function dex-namespace-shell {
  if [[ $# -ne 1 ]]; then
    echo "Usage: dex-namespace-shell [namespace]"
    return 1
  fi

  CLUSTER_ID="${CLUSTER_ID:-noclusterid}"
  DEX_NS=$1

  if [[ "$CLUSTER_ID" == 'noclusterid' ]]; then
        echo "CLUSTER_ID should be set"
        return 1
  fi

  cst && dexw -v --cluster-id ${CLUSTER_ID} -cst $CST --mow-env dev --auth cst zsh
}

function dex-stern-dex-api {
  if [[ $# -ne 1 ]]; then
    echo "Usage: dex-stern-dex-api [namespace]"
    return 1
  fi

  CLUSTER_ID="${CLUSTER_ID:-noclusterid}"
  DEX_NS=$1

  if [[ "$CLUSTER_ID" == 'noclusterid' ]]; then
        echo "CLUSTER_ID should be set"
        return 1
  fi

  cst && dexw -a cst --cluster-id ${CLUSTER_ID} -cst $CST --mow-env dev stern -n $DEX_NS -l app.kubernetes.io/name=dex-app-api
}

function dex-open-private-stack-bteke {
  CLUSTER_ID=$1
    if [[ -z $CLUSTER_ID ]]; then
        echo "Usage: dex-open-private-stack-bteke cluster-id" >&2
        return 1
    fi
  dexw -cst $CST --cluster-id cluster-8gr6wwvt --mow-env priv --csi-workspace bteke k9s
}


function dex-create-service-in-stack {
    dex-cst; curl -H 'Content-Type: application/json' -d '{
      "name": "snemeth-cde-DEX7712",
      "env": "dex-priv-default-aws-env-3",
      "config": {
          "properties": {
              "loadbalancer.internal":"true",
              "cde.version": "1.18.0"
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

function dex-create-private-stack {
  echo "Moonlander / make"
  cd $CSI_HOME/moonlander && make;


  gimme-aws-creds
  goto-dex
  # 1. make protos api-docs gen-mocks

  # 2. moonlander install
  DATE_OF_START=`date +%F-%H%M%S`
  logfilename="~/.dex/logs/dexprivatestack_$DATE_OF_START.log"
  mow-priv ./dev-tools/moonlander-cp.sh install ${USER} --ttl 168 | tee $logfilename

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

  dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS set image deployment/$DEX_APP_DEPL dex-app-api=docker-registry.infra.cloudera.com/snemeth/dex-runtime-api-server:$NEW_IMAGE_TAG

  echo "Listing modified image of dex-app-api (runtime): "
	dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS describe deployment $DEX_APP_DEPL | grep -i image

	dexw -cst $CST --cluster-id $CLUSTER_ID --mow-env priv kubectl -n $DEX_APP_NS get pods
}

function dex-private-stack-get-logs-follow {
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


function dex-dexk() {
    CLUSTER_ID=$1
    if [[ -z $CLUSTER_ID ]]; then
        echo "Usage: dex-dexk cluster-id" >&2
        return 1
    fi
    cst && dexk --cluster-id $clusterId --cdp-token $CST --ingress dex --mow-env priv --workspace-name ${USER}
}

###################################################################### DEX RUNTIME ######################################################################

dex-export-gopath