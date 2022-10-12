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


function dex-build-runtime {
		if [ -z ${REGISTRY_NAMESPACE+x} ]; then 
			echo "REGISTRY_NAMESPACE is not set. Call 'dex-export-runtime-build-env' first";
			return
		else 
			echo "REGISTRY_NAMESPACE set to '$REGISTRY_NAMESPACE'"; 
		fi


    # Should call manually: dex-export-runtime-build-env
  	cd $DEX_DEV_ROOT/docker
    make dex-runtime-api-server
    docker tag docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/dex-runtime-api-server:${VERSION} docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/dex-runtime-api-server:${VERSION}-${JIRA_NUM}
    # docker tag docker-registry.infra.cloudera.com/cloudera/dex/dex-runtime-api-server:${VERSION} docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/dex-runtime-api-server:${VERSION}-${JIRA_NUM}
    docker push docker-registry.infra.cloudera.com/${REGISTRY_NAMESPACE}/dex-runtime-api-server:${VERSION}-${JIRA_NUM}
    cd -
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