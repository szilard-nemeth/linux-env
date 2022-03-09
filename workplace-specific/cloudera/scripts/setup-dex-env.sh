#!/usr/bin/env bash

echo "Setting up DEX env..."
# asdf setup
. /usr/local/opt/asdf/libexec/asdf.sh

#Go setup
export GOPATH=$(go env GOPATH)
export PATH=$PATH:$GOPATH/bin
export GOOS=darwin