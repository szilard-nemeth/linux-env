#!/usr/bin/env bash

echo "Setting up DEX env..."
# asdf setup
. /usr/local/opt/asdf/libexec/asdf.sh

#Go setup
export GOPATH=$(go env GOPATH)
export PATH=$PATH:$GOPATH/bin
export GOOS=darwin

# https://github.infra.cloudera.com/SRE/cloud-users/tree/master/scripts/cloudera-cloud-users
source "$(brew --prefix)/lib/cloudera-cloud-users.sh"
autoload -U +X bashcompinit && bashcompinit
autoload -U +X compinit && compinit

# https://github.infra.cloudera.com/pages/SRE/docs/AWS/usage_command-line/#install-and-configure
export MOW_AUTH_TOOL=none

complete -C '/usr/local/bin/aws_completer' aws


export CSI_HOME="$HOME/development/cloudera/cde/cloud-services-infra/"
export DEX_DEV_TOOLS="$HOME/development/cloudera/cde/dex/dev-tools"
export PATH=$PATH:$CSI_HOME/bin:$CSI_HOME/moonlander:$DEX_DEV_TOOLS


#################################### DEX functions ####################################

# https://github.infra.cloudera.com/CDH/dex-utils/tree/master/cdp-token-chrome
cst () {
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