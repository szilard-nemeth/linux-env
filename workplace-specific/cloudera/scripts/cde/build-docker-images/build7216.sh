#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
. $DIR/common.sh

if [ -z "$DEX_HOME" ]; then
  echo "DEX_HOME is unset. Please set and export it!" 1>&2
  exit 1
fi

export VERSION=7.2.16.0-999
export PYTHON_VERSION_FOR_BUILDER=python38
export FORM_FACTOR=pc
export CDP_PLATFORM=7.2.16

. $DIR/build-generic.sh